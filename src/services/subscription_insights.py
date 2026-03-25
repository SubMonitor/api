from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta

from src.db.subs.models import SubscriptionUsageEvent
from src.db.subs.schemas import (
    InsightAction,
    Period,
    SubscriptionActionPlanResponse,
    SubscriptionAlert,
    SubscriptionCategorySpend,
    SubscriptionForecastPoint,
    SubscriptionInsightsResponse,
    SubscriptionInsightsSummary,
    SubscriptionRecommendation,
    SubscriptionResponse,
    SubscriptionUpcomingCharge,
    SubscriptionUsageStatus,
    UsageSignal,
)


TWO_PLACES = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")
USAGE_WEIGHTS = {
    UsageSignal.used.value: 1.0,
    UsageSignal.light.value: 0.45,
    UsageSignal.unused.value: 0.0,
}

CATEGORY_ALTERNATIVES = {
    "streaming": ["Кинопоиск", "Okko", "Premier"],
    "music": ["Яндекс Музыка", "VK Музыка", "Звук"],
    "cloud": ["Google One", "Яндекс 360", "Dropbox"],
    "software": ["OnlyOffice", "LibreOffice", "Figma Starter"],
    "delivery": ["Самокат", "СберПрайм", "Яндекс Плюс"],
    "education": ["Stepik", "Coursera", "Skillbox"],
    "gaming": ["Xbox Game Pass", "PlayStation Plus", "GeForce NOW"],
}

CATEGORY_KEYWORDS = {
    "streaming": ("stream", "video", "movie", "series", "tv", "кино", "видео", "сериал"),
    "music": ("music", "audio", "музык", "аудио"),
    "cloud": ("cloud", "storage", "drive", "обла", "хран"),
    "software": ("software", "saas", "design", "dev", "office", "софт", "прилож"),
    "delivery": ("delivery", "food", "express", "достав", "еда"),
    "education": ("course", "learn", "study", "edu", "курс", "обуч", "школ"),
    "gaming": ("game", "gaming", "игр", "console"),
}


def build_insights(
    subscriptions: list[SubscriptionResponse],
    usage_events: list[SubscriptionUsageEvent],
) -> SubscriptionInsightsResponse:
    now = datetime.now(timezone.utc)
    active_subscriptions = [subscription for subscription in subscriptions if subscription.is_active]
    usage_map = _group_usage_events(usage_events)
    usage_reviews = [
        _build_usage_status(subscription, usage_map.get(subscription.id, []), now)
        for subscription in active_subscriptions
    ]
    usage_reviews.sort(key=lambda item: (_usage_priority(item.status), -float(item.monthly_cost), item.service_name.lower()))

    yearly_forecast = _build_yearly_forecast(active_subscriptions, now)
    upcoming_charges = _build_upcoming_charges(active_subscriptions, now)
    category_breakdown = _build_category_breakdown(active_subscriptions)
    alerts = _build_alerts(active_subscriptions, usage_reviews, upcoming_charges)
    recommendations = _build_recommendations(active_subscriptions, usage_reviews)

    monthly_total = _money(sum((_monthly_cost(subscription) for subscription in active_subscriptions), ZERO_MONEY))
    yearly_total = _money(sum((point.total_cost for point in yearly_forecast), ZERO_MONEY))
    upcoming_30_days_total = _money(
        sum((charge.cost for charge in upcoming_charges if charge.days_left <= 30), ZERO_MONEY)
    )
    savings_opportunity_total = _money(
        sum((recommendation.estimated_yearly_savings for recommendation in recommendations), ZERO_MONEY)
    )
    needs_attention_count = sum(1 for review in usage_reviews if review.status != "healthy")

    summary = SubscriptionInsightsSummary(
        total_subscriptions=len(subscriptions),
        active_subscriptions=len(active_subscriptions),
        monthly_total=monthly_total,
        yearly_total=yearly_total,
        upcoming_30_days_total=upcoming_30_days_total,
        savings_opportunity_total=savings_opportunity_total,
        needs_attention_count=needs_attention_count,
    )

    return SubscriptionInsightsResponse(
        summary=summary,
        category_breakdown=category_breakdown,
        yearly_forecast=yearly_forecast,
        upcoming_charges=upcoming_charges,
        alerts=alerts[:6],
        recommendations=recommendations[:4],
        usage_reviews=usage_reviews,
    )


def build_action_plan(
    subscription: SubscriptionResponse,
    user_email: str,
    action: InsightAction,
) -> SubscriptionActionPlanResponse:
    verb = "приостановить" if action == InsightAction.pause else "отменить"
    noun = "паузу" if action == InsightAction.pause else "отмену"
    next_charge = _format_date(subscription.next_payment_date)

    subject = f"Запрос на {noun} подписки {subscription.name}"
    body = (
        "Здравствуйте!\n\n"
        f"Прошу {verb} мою подписку \"{subscription.name}\".\n"
        f"Аккаунт пользователя: {user_email}\n"
        f"Категория: {subscription.category}\n"
        f"Ближайшее списание: {next_charge}\n\n"
        "Прошу подтвердить обработку запроса и сообщить, будут ли дополнительные списания.\n\n"
        "Спасибо!"
    )

    return SubscriptionActionPlanResponse(
        subscription_id=subscription.id,
        service_name=subscription.name,
        action=action,
        subject=subject,
        body=body,
        copy_text=f"Тема: {subject}\n\n{body}",
        copy_hint="Скопируйте текст в чат поддержки, форму обратной связи или письмо сервису.",
        steps=[
            "Откройте настройки платежей или чат поддержки сервиса.",
            f"Вставьте шаблон для подписки {subscription.name}.",
            "Попросите письменное подтверждение и проверьте дату следующего списания.",
        ],
    )


def _build_category_breakdown(subscriptions: list[SubscriptionResponse]) -> list[SubscriptionCategorySpend]:
    if not subscriptions:
        return []

    totals: dict[str, dict[str, Decimal | int]] = {}
    total_monthly = ZERO_MONEY

    for subscription in subscriptions:
        monthly_cost = _monthly_cost(subscription)
        yearly_cost = _yearly_cost(subscription)
        total_monthly += monthly_cost
        bucket = totals.setdefault(
            subscription.category,
            {"monthly_cost": ZERO_MONEY, "yearly_cost": ZERO_MONEY, "subscriptions_count": 0},
        )
        bucket["monthly_cost"] += monthly_cost
        bucket["yearly_cost"] += yearly_cost
        bucket["subscriptions_count"] += 1

    result: list[SubscriptionCategorySpend] = []
    for category, values in totals.items():
        monthly_cost = _money(values["monthly_cost"])
        yearly_cost = _money(values["yearly_cost"])
        share = 0.0 if total_monthly == ZERO_MONEY else float((monthly_cost / total_monthly) * Decimal("100"))
        result.append(
            SubscriptionCategorySpend(
                category=category,
                monthly_cost=monthly_cost,
                yearly_cost=yearly_cost,
                subscriptions_count=int(values["subscriptions_count"]),
                share_percent=round(share, 1),
            )
        )

    result.sort(key=lambda item: (-float(item.monthly_cost), item.category.lower()))
    return result


def _build_yearly_forecast(
    subscriptions: list[SubscriptionResponse],
    now: datetime,
) -> list[SubscriptionForecastPoint]:
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    buckets: dict[str, Decimal] = {}
    charges_count: dict[str, int] = {}
    ordered_months: list[str] = []

    for index in range(12):
        month_key = (month_start + relativedelta(months=index)).strftime("%Y-%m")
        buckets[month_key] = ZERO_MONEY
        charges_count[month_key] = 0
        ordered_months.append(month_key)

    forecast_end = month_start + relativedelta(months=12)
    for subscription in subscriptions:
        charge_at = _ensure_utc(subscription.next_payment_date)
        if charge_at is None:
            continue

        while charge_at < forecast_end:
            month_key = charge_at.strftime("%Y-%m")
            if month_key in buckets:
                buckets[month_key] += Decimal(subscription.cost)
                charges_count[month_key] += 1

            if subscription.billing_cycle == Period.once:
                break

            next_charge = subscription.billing_cycle.add_value(charge_at)
            if next_charge is None or next_charge <= charge_at:
                break
            charge_at = _ensure_utc(next_charge)

    return [
        SubscriptionForecastPoint(
            month=month_key,
            total_cost=_money(buckets[month_key]),
            charges_count=charges_count[month_key],
        )
        for month_key in ordered_months
    ]


def _build_upcoming_charges(
    subscriptions: list[SubscriptionResponse],
    now: datetime,
) -> list[SubscriptionUpcomingCharge]:
    charges = []
    for subscription in subscriptions:
        charge_at = _ensure_utc(subscription.next_payment_date)
        if charge_at is None:
            continue

        days_left = max(0, (charge_at.date() - now.date()).days)
        charges.append(
            SubscriptionUpcomingCharge(
                subscription_id=subscription.id,
                service_name=subscription.name,
                charge_date=charge_at,
                days_left=days_left,
                cost=_money(Decimal(subscription.cost)),
                billing_cycle=subscription.billing_cycle,
            )
        )

    charges.sort(key=lambda item: (item.days_left, item.charge_date, item.service_name.lower()))
    return charges[:8]


def _build_alerts(
    subscriptions: list[SubscriptionResponse],
    usage_reviews: list[SubscriptionUsageStatus],
    upcoming_charges: list[SubscriptionUpcomingCharge],
) -> list[SubscriptionAlert]:
    alerts: list[SubscriptionAlert] = []
    usage_by_subscription = {review.subscription_id: review for review in usage_reviews}

    for charge in upcoming_charges:
        if charge.days_left > 3:
            continue
        alerts.append(
            SubscriptionAlert(
                code="upcoming_charge",
                severity="high" if charge.days_left <= 1 else "medium",
                subscription_id=charge.subscription_id,
                service_name=charge.service_name,
                title=f"Скорое списание: {charge.service_name}",
                message=f"До следующего списания осталось {charge.days_left} дн., сумма {charge.cost}.",
                recommended_action="Проверьте, нужна ли подписка перед ближайшим платежом.",
                potential_savings=ZERO_MONEY,
            )
        )

    for subscription in subscriptions:
        usage = usage_by_subscription.get(subscription.id)
        if usage is None:
            continue

        if usage.status == "inactive":
            alerts.append(
                SubscriptionAlert(
                    code="inactive_subscription",
                    severity="high",
                    subscription_id=subscription.id,
                    service_name=subscription.name,
                    title=f"Подписка не используется: {subscription.name}",
                    message="Система давно не видела usage-активности по этой подписке.",
                    recommended_action="Поставьте сервис на паузу или отмените его до следующего списания.",
                    potential_savings=_yearly_cost(subscription),
                )
            )
        elif usage.status == "watch":
            alerts.append(
                SubscriptionAlert(
                    code="usage_review",
                    severity="low",
                    subscription_id=subscription.id,
                    service_name=subscription.name,
                    title=f"Нужна проверка пользы: {subscription.name}",
                    message="Использование сервиса низкое или по нему пока мало сигналов.",
                    recommended_action="Сравните тариф, отметьте реальное использование или отключите сервис.",
                    potential_savings=_money(_yearly_cost(subscription) / Decimal("2")),
                )
            )

    alerts.sort(
        key=lambda item: (
            _severity_priority(item.severity),
            -float(item.potential_savings),
            item.service_name.lower(),
        )
    )
    return alerts


def _build_recommendations(
    subscriptions: list[SubscriptionResponse],
    usage_reviews: list[SubscriptionUsageStatus],
) -> list[SubscriptionRecommendation]:
    subscription_by_id = {subscription.id: subscription for subscription in subscriptions}
    recommendations: list[SubscriptionRecommendation] = []

    for usage in usage_reviews:
        if usage.status == "healthy":
            continue

        subscription = subscription_by_id.get(usage.subscription_id)
        if subscription is None:
            continue

        if usage.status == "inactive":
            reason = "Подписка не используется, но продолжает участвовать в регулярных списаниях."
            savings = _yearly_cost(subscription)
        else:
            reason = "Пользы от сервиса меньше, чем ожидается. Имеет смысл сравнить тариф и аналоги."
            savings = _money(_yearly_cost(subscription) / Decimal("2"))

        recommendations.append(
            SubscriptionRecommendation(
                subscription_id=subscription.id,
                service_name=subscription.name,
                category=subscription.category,
                reason=reason,
                alternative_services=_alternatives_for_category(subscription.category),
                estimated_yearly_savings=savings,
                action_hint="Сравните аналоги в категории, семейные тарифы или временную паузу сервиса.",
            )
        )

    recommendations.sort(
        key=lambda item: (-float(item.estimated_yearly_savings), item.service_name.lower())
    )
    return recommendations


def _build_usage_status(
    subscription: SubscriptionResponse,
    events: list[SubscriptionUsageEvent],
    now: datetime,
) -> SubscriptionUsageStatus:
    monthly_cost = _monthly_cost(subscription)
    last_event = events[0] if events else None
    recent_events = [
        event for event in events
        if _ensure_utc(event.created_at) is not None and _ensure_utc(event.created_at) >= now - timedelta(days=30)
    ]

    if not events:
        age_days = max(0, (now.date() - _ensure_utc(subscription.created_at).date()).days)
        status = "watch" if age_days >= 21 else "no_data"
        status_label = "Нужны данные" if status == "watch" else "Пока без данных"
        return SubscriptionUsageStatus(
            subscription_id=subscription.id,
            service_name=subscription.name,
            status=status,
            status_label=status_label,
            usage_score=0,
            last_signal=None,
            last_recorded_at=None,
            monthly_cost=monthly_cost,
            recommended_action="Добавьте usage-отметки, чтобы система могла выявлять неактивные подписки.",
        )

    if not recent_events:
        return SubscriptionUsageStatus(
            subscription_id=subscription.id,
            service_name=subscription.name,
            status="inactive",
            status_label="Не используется",
            usage_score=10,
            last_signal=UsageSignal(last_event.signal),
            last_recorded_at=_ensure_utc(last_event.created_at),
            monthly_cost=monthly_cost,
            recommended_action="За последний месяц нет usage-активности. Проверьте, нужен ли сервис.",
        )

    sample = recent_events[:5]
    average_score = sum(USAGE_WEIGHTS.get(event.signal, 0.0) for event in sample) / len(sample)
    usage_score = max(0, min(100, int(round(average_score * 100))))

    if average_score >= 0.7:
        status = "healthy"
        status_label = "Используется"
        action = "Текущая подписка выглядит полезной. Следите за датой следующего списания."
    elif average_score >= 0.35:
        status = "watch"
        status_label = "Под вопросом"
        action = "Использование ниже среднего. Сравните тариф или проверьте альтернативы."
    else:
        status = "inactive"
        status_label = "Не используется"
        action = "Пользы почти нет. Лучше поставить сервис на паузу или отменить."

    return SubscriptionUsageStatus(
        subscription_id=subscription.id,
        service_name=subscription.name,
        status=status,
        status_label=status_label,
        usage_score=usage_score,
        last_signal=UsageSignal(last_event.signal),
        last_recorded_at=_ensure_utc(last_event.created_at),
        monthly_cost=monthly_cost,
        recommended_action=action,
    )


def _group_usage_events(events: list[SubscriptionUsageEvent]) -> dict[int, list[SubscriptionUsageEvent]]:
    grouped: dict[int, list[SubscriptionUsageEvent]] = defaultdict(list)
    for event in events:
        grouped[event.subscription_id].append(event)

    for subscription_id, subscription_events in grouped.items():
        subscription_events.sort(key=lambda item: (_ensure_utc(item.created_at), item.id), reverse=True)

    return grouped


def _monthly_cost(subscription: SubscriptionResponse) -> Decimal:
    cost = Decimal(subscription.cost)
    if subscription.billing_cycle == Period.month:
        return _money(cost)
    if subscription.billing_cycle == Period.year:
        return _money(cost / Decimal("12"))
    if subscription.billing_cycle == Period.week:
        return _money(cost * Decimal("52") / Decimal("12"))
    return ZERO_MONEY


def _yearly_cost(subscription: SubscriptionResponse) -> Decimal:
    if subscription.billing_cycle == Period.once:
        charge_date = _ensure_utc(subscription.next_payment_date)
        if charge_date is None:
            return ZERO_MONEY
        now = datetime.now(timezone.utc)
        return _money(Decimal(subscription.cost) if charge_date <= now + relativedelta(months=12) else ZERO_MONEY)
    return _money(_monthly_cost(subscription) * Decimal("12"))


def _alternatives_for_category(category: str) -> list[str]:
    normalized_category = _normalize_category(category)
    return CATEGORY_ALTERNATIVES.get(
        normalized_category,
        ["Бесплатный тариф", "Семейный тариф", "Годовая оплата со скидкой"],
    )


def _normalize_category(category: str) -> str:
    value = (category or "").strip().lower()
    for normalized, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in value for keyword in keywords):
            return normalized
    return value


def _usage_priority(status: str) -> int:
    if status == "inactive":
        return 0
    if status == "watch":
        return 1
    if status == "no_data":
        return 2
    return 3


def _severity_priority(severity: str) -> int:
    if severity == "high":
        return 0
    if severity == "medium":
        return 1
    return 2


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_date(value: datetime | None) -> str:
    dt_value = _ensure_utc(value)
    if dt_value is None:
        return "-"
    return dt_value.strftime("%d.%m.%Y")
