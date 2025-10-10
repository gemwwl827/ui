# cases/test_model_call.py
from llm.llm_client import call_model

if __name__ == "__main__":
    prompt = "谈谈纳斯达克"
    result = call_model(prompt)
    print("📦 模型响应：", result)






# from llm.llm_client import call_model
#
# prompt = "谈谈纳斯达克"
#
# # ✅ 调用本地 DeepSeek 模型
# result = call_model(prompt, source="deepseek")
# print("📦 DeepSeek 响应：", result)
