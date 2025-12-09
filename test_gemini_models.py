# coding=utf-8
"""
测试 Gemini 模型可用性
"""

import os
import google.generativeai as genai

# 从环境变量获取 API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("❌ 请设置环境变量 GEMINI_API_KEY")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# 要测试的模型列表
MODELS_TO_TEST = [
    "gemini-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-latest",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-thinking-exp",
]

print("=" * 60)
print("测试 Gemini 模型可用性")
print("=" * 60)
print()

test_prompt = "你好，请回复'测试成功'"

for model_name in MODELS_TO_TEST:
    try:
        print(f"测试模型: {model_name}...", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(test_prompt)
        result = response.text.strip()
        print(f"✅ 成功")
        print(f"   响应: {result[:50]}...")
        print()
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            print(f"❌ 模型不存在")
        elif "not supported" in error_msg.lower():
            print(f"❌ 模型不支持 generateContent")
        else:
            print(f"❌ 错误: {error_msg[:50]}...")
        print()

print("=" * 60)
print("测试完成")
print("=" * 60)

