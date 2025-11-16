import os
import requests
from typing import Optional, Dict

def summarize_with_gemini(
    api_key: str,
    text: str,
    *,
    model: str = 'gemini-2.5-flash',
    counts: Optional[Dict[str, int]] = None,
    language: str = 'ru'
) -> str:
  
    if not api_key:
        return ''
    try:
        import google.generativeai as genai
    except Exception:
        return ''

    counts = counts or {'signature': 0, 'stamp': 0, 'qr_code': 0}
    text_trimmed = (text[:12000] + '\n...') if text and len(text) > 12000 else (text or '')

    system_rules = (
        "Ты помощник, который кратко суммаризует ДАННЫЙ текст документа без выдумок. "
        "Всегда отвечай на русском. Структура ответа: \n"
        "1) Одно-два предложения: о чём документ (тип, цель, ключевые стороны/даты, если явно указаны).\n"
        "2) 3-6 буллетов с ключевыми пунктами (обязательства/сроки/суммы/объект работ — только если явно присутствуют).\n"
        "3) Итог: статус подписания/печати/QR — используй предоставленную статистику детекций, не делай выводов без фактов.\n"
        "Правила: не выдумывай факты, не делай юридических интерпретаций, если чего-то нет в тексте — напиши 'не указано'."
    )

    user_prompt = (
        f"Статистика детекций: подписи={counts.get('signature',0)}, печати={counts.get('stamp',0)}, QR={counts.get('qr_code',0)}.\n"
        "Ниже сырой текст документа для суммаризации (используй только его):\n\n" + text_trimmed
    )

    try:
        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(model)
        resp = model_client.generate_content([
            system_rules,
            user_prompt
        ])
        if hasattr(resp, 'text'):
            return (resp.text or '').strip()
        # SDK shapes can differ; fallback
        out = getattr(resp, 'candidates', None)
        if out:
            finish = out[0]
            parts = getattr(getattr(finish, 'content', None), 'parts', None)
            if parts and len(parts) and hasattr(parts[0], 'text'):
                return (parts[0].text or '').strip()
        return ''
    except Exception:
        return ''


def summarize_with_perplexity(
    api_key: str,
    text: str,
    *,
    model: str = 'llama-3.1-70b-instruct',
    counts: Optional[Dict[str, int]] = None,
    language: str = 'ru'
) -> str:
    if not api_key:
        return ''

    counts = counts or {'signature': 0, 'stamp': 0, 'qr_code': 0}

    # Ограничим размер текста для запроса (примерно до 12k символов)
    text_trimmed = (text[:12000] + '\n...') if text and len(text) > 12000 else (text or '')

    system_rules = (
        "Ты помощник, который кратко суммаризует ДАННЫЙ текст документа без выдумок. "
        "Всегда отвечай на русском. Структура ответа: \n"
        "1) Одно-два предложения: о чём документ (тип, цель, ключевые стороны/даты, если явно указаны).\n"
        "2) 3-6 буллетов с ключевыми пунктами (обязательства/сроки/суммы/объект работ — только если явно присутствуют).\n"
        "3) Итог: статус подписания/печати/QR — используй предоставленную статистику детекций, не делай выводов без фактов.\n"
        "Правила: не выдумывай факты, не делай юридических интерпретаций, если чего-то нет в тексте — напиши 'не указано'."
    )

    user_content = (
        f"Статистика детекций: подписи={counts.get('signature',0)}, печати={counts.get('stamp',0)}, QR={counts.get('qr_code',0)}.\n"
        "Ниже сырой текст документа для суммаризации (используй только его):\n\n" + text_trimmed
    )

    try:
        resp = requests.post(
            'https://api.perplexity.ai/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': model,
                'temperature': 0.2,
                'messages': [
                    {'role': 'system', 'content': system_rules},
                    {'role': 'user', 'content': user_content}
                ]
            },
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        return content or ''
    except Exception:
        return ''
