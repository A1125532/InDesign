from flask import Flask, request, render_template, jsonify, send_from_directory
import subprocess, os, sys, json
from opencc import OpenCC  # 這裡整合你的 change.py 功能

# -------------------------------
# 基本設定
# -------------------------------
print("🔥 Flask 正在使用的 Python 解譯器：", sys.executable)
print("🐍 Python 版本：", sys.version)

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# -------------------------------
# 初始化 OpenCC + 自訂字典
# -------------------------------
cc = OpenCC('s2tw')
custom_dict = {
    "表现": "表現",
    "錶現": "表現",
    "软件": "軟體",
    "了解": "瞭解",
    "面包": "麵包"
}

def custom_convert(text):
    """先用 OpenCC 轉換，再強制覆蓋自訂詞彙"""
    converted = cc.convert(text)
    for s, t in custom_dict.items():
        converted = converted.replace(s, t)
        converted = converted.replace(cc.convert(s), t)
    return converted

def convert_text_in_json(data):
    """遞迴轉換 JSON 裡的所有文字"""
    if isinstance(data, dict):
        return {k: convert_text_in_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_text_in_json(item) for item in data]
    elif isinstance(data, str):
        # 避免轉換公式或數字
        if any(sym in data for sym in ["\\frac", "\\sqrt", "^", "_", "+", "-", "=", "{", "}", "%", "/", "\\text", "\\mathrm"]):
            return data
        if data.replace('.', '', 1).isdigit():
            return data
        return custom_convert(data)
    else:
        return data

def process_json_file(input_path, output_path):
    """開啟並轉換單一 JSON 檔"""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    converted = convert_text_in_json(data)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
    print(f"✅ 已輸出繁體 JSON：{output_path}")

# -------------------------------
# Flask 路由
# -------------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """接收 PDF 檔案上傳"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未選擇檔案'}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    print(f"✅ 已上傳檔案：{file.filename} -> {save_path}")

    return jsonify({
        'message': f'上傳成功：{file.filename}',
        'filename': file.filename
    })


@app.route('/process', methods=['POST'])
def process():
    """執行 test_reducto.py 並轉繁體"""
    data = request.get_json()
    rules = data.get('rules', '')
    filename = data.get('filename', '')

    if not filename:
        return jsonify({'error': '沒有提供檔名'}), 400

    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(pdf_path):
        return jsonify({'error': f'找不到檔案：{pdf_path}'}), 404

    try:
        # 🚀 執行 test_reducto.py
        reducto_result = subprocess.run(
            ['python', 'test_reducto.py', pdf_path],
            capture_output=True, text=True
        )

        print("test_reducto.py 輸出：", reducto_result.stdout)
        print("test_reducto.py 錯誤：", reducto_result.stderr)

        # ✅ 根據原始檔名推算 JSON 檔案
        json_name = os.path.splitext(filename)[0] + '.json'
        src_json_path = os.path.join('uploads', json_name)
        dst_json_path = os.path.join(DOWNLOAD_FOLDER, json_name)

        if os.path.exists(src_json_path):
            os.replace(src_json_path, dst_json_path)
            print(f"📦 已搬移 JSON：{src_json_path} → {dst_json_path}")
        elif not os.path.exists(dst_json_path):
            print("⚠️ 找不到任何輸出 JSON 檔案")
            return jsonify({'error': f'找不到輸出檔案：{json_name}'}), 404

        # 🈶 經過 change.py 的繁體轉換
        merged_name = os.path.splitext(filename)[0] + '_merged.json'
        merged_path = os.path.join(DOWNLOAD_FOLDER, merged_name)
        process_json_file(dst_json_path, merged_path)

        # ✅ 回傳新檔案名稱
        return jsonify({
            'message': '✅ 已完成 test_reducto.py + 繁體轉換！',
            'json_filename': merged_name
        })

    except Exception as e:
        print("❌ 錯誤：", e)
        return jsonify({'error': f'程式執行錯誤：{e}'})


@app.route('/download/<path:filename>')
def download_file(filename):
    """讓前端下載 JSON"""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
