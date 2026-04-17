from groq import Groq
import os
from . import crud
import redis.asyncio as redis

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def chatbot_response(message: str, redis_client: redis.Redis):
    # Lấy tất cả link để AI biết context
    links = await crud.get_all_links()
    
    context = "Bạn là trợ lý thông minh của Linkly - một URL Shortener.\n"
    context += "Các lệnh bạn có thể hỗ trợ:\n"
    context += "- Tạo link ngắn\n"
    context += "- Xem thống kê click\n"
    context += "- Xóa link\n"
    context += "- Liệt kê tất cả link\n\n"
    context += f"Danh sách link hiện tại: {links}\n\n"
    context += "Hãy trả lời ngắn gọn, thân thiện và bằng tiếng Việt."

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": message}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=500
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Xin lỗi, hiện tại chatbot đang gặp vấn đề: {str(e)}"
