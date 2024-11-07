import openai
from decouple import config
import tiktoken
import logging
logger = logging.getLogger(__name__)

model=config('model_name')



def call_openai_api(prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful interviewer."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=int(max_tokens),
        temperature=float(temperature),
        top_p=float(top_p),
        frequency_penalty=float(frequency_penalty),
        presence_penalty=float(presence_penalty)
    )
    return response

def calculate_token_cost(prompt, response):
    encoding = tiktoken.encoding_for_model(model)
    input_tokens = len(encoding.encode(prompt))

    if not isinstance(response, str):
        response = str(response)

    output_tokens = len(encoding.encode(response))
    total_tokens = input_tokens + output_tokens
    cost_per_token = 0.0002
    cost = (total_tokens / 1000) * cost_per_token

    logging.info({
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost": cost,
        "prompt": prompt
    })

