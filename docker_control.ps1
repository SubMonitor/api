param(
    [string]$action
)

function Show-Menu {
    Clear-Host
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "          Управление Docker-контейнерами" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1) Запустить контейнеры (docker-compose up -d)" -ForegroundColor Green
    Write-Host "  2) Остановить контейнеры (docker-compose down)" -ForegroundColor Red
    Write-Host "  3) Пересобрать и запустить (up -d --build)" -ForegroundColor Magenta
    Write-Host "  4) Показать логи API" -ForegroundColor Blue
    Write-Host "  5) Подключиться к SQL (psql)" -ForegroundColor Cyan
    Write-Host "  6) Перезапустить API (restart)" -ForegroundColor Yellow
    Write-Host "  7) Очистить всё (down -v)" -ForegroundColor DarkRed
    Write-Host "  8) Выход" -ForegroundColor Gray
    Write-Host ""
}

if ($action) {
    $choice = $action
} else {
    do {
        Show-Menu
        $choice = Read-Host "Введите номер"
        switch ($choice) {
            "1" {
                Write-Host "Запуск контейнеров..." -ForegroundColor Green
                docker-compose up -d
            }
            "2" {
                Write-Host "Остановка контейнеров..." -ForegroundColor Red
                docker-compose down
            }
            "3" {
                Write-Host "Пересборка и запуск..." -ForegroundColor Magenta
                docker-compose up -d --build
            }
            "4" {
                Write-Host "Логи API (Ctrl+C для выхода)..." -ForegroundColor Blue
                docker-compose logs -f api
            }
            "5" {
                Write-Host "Подключение к SQL..." -ForegroundColor Cyan
                docker exec -it db psql -U postgres -d db
            }
            "6" {
                Write-Host "Перезапуск API..." -ForegroundColor Yellow
                docker-compose restart api
            }
            "7" {
                Write-Host "Остановка и удаление томов..." -ForegroundColor DarkRed
                docker-compose down -v
            }
            "8" {
                Write-Host "Выход" -ForegroundColor Gray
                exit
            }
            default {
                Write-Host "Неверный выбор" -ForegroundColor Red
                pause
            }
        }
        if ($choice -ne "8") {
            pause
        }
    } while ($choice -ne "8")
}