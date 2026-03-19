from src.core import config
import openai


client = openai.OpenAI(
    api_key=config.yandex_gpt_api_key,
    base_url=config.yandex_gpt_api_base_url,
    project=config.yandex_gpt_api_project,
)

def llp_sub_parsing(s: str):
    return client.responses.create(
        prompt={
            "id": "fvtvtql9v1f3gc10qg5c",
        },
        input=s).output_text
