from flask import Flask, request, render_template, jsonify, send_from_directory
import subprocess, os, sys, json, shutil
from opencc import OpenCC

# -------------------------------
# 基本設定
# -------------------------------
print("🔥 Flask 正在使用的 Python 解譯器：", sys.executable)
print("🐍 Python 版本：", sys.version)

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")
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
    converted = cc.convert(text)
    for s, t in custom_dict.items():
        converted = converted.replace(s, t)
        converted = converted.replace(cc.convert(s), t)
    return converted

def convert_text_in_json(data):
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
    """開啟並轉換 JSON"""
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
    """接收 PDF 上傳"""
    if 'file' not in request.files:
        return jsonify({'error': '沒有檔案'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未選擇檔案'}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)
    print(f"✅ 已上傳檔案：{file.filename} → {save_path}")

    return jsonify({'message': f'上傳成功：{file.filename}', 'filename': file.filename})

@app.route('/process', methods=['POST'])
def process():
    """執行 test_reducto.py → 繁體轉換 → 呼叫 convert 子專案"""
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': '沒有提供檔名'}), 400

    pdf_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(pdf_path):
        return jsonify({'error': f'找不到檔案：{pdf_path}'}), 404

    try:
        # ------------------------------------------------------
        # 🚀 第一步：執行 test_reducto.py
        # ------------------------------------------------------
        current_dir = os.path.dirname(__file__)
        test_script = os.path.join(current_dir, 'test_reducto.py')

        reducto_result = subprocess.run(
            [sys.executable, test_script, pdf_path],
            capture_output=True, text=True, cwd=current_dir
        )
        print("test_reducto.py 輸出：", reducto_result.stdout)
        print("test_reducto.py 錯誤：", reducto_result.stderr)

        # ------------------------------------------------------
        # 🚀 第二步：確認 JSON 輸出，並進行繁體轉換
        # ------------------------------------------------------
        json_name = os.path.splitext(filename)[0] + '.json'
        src_json_path = os.path.join(current_dir, 'downloads', json_name)
        dst_json_path = os.path.join(DOWNLOAD_FOLDER, json_name)

        if os.path.exists(src_json_path):
            os.replace(src_json_path, dst_json_path)
            print(f"📦 已搬移 JSON：{src_json_path} → {dst_json_path}")
        else:
            return jsonify({'error': f'找不到輸出檔案：{json_name}'}), 404

        merged_name = os.path.splitext(filename)[0] + '_merged.json'
        merged_path = os.path.join(DOWNLOAD_FOLDER, merged_name)
        process_json_file(dst_json_path, merged_path)

        # ------------------------------------------------------
        # 🚀 第三步：複製 merged.json 給 convert 處理
        # ------------------------------------------------------
        converter_examples_dir = os.path.join(current_dir, '..', 'convert', 'knowledge', 'math_exam', 'examples')
        os.makedirs(converter_examples_dir, exist_ok=True)

        converter_input_path = os.path.join(converter_examples_dir, os.path.basename(merged_path))
        shutil.copy(merged_path, converter_input_path)
        print(f"📂 已複製 {merged_path} → {converter_input_path}")

        # ------------------------------------------------------
        # 🚀 第四步：呼叫 convert/server/app.py（使用 UTF-8 & 固定分類）
        # ------------------------------------------------------
        converter_script = os.path.join(current_dir, '..', 'convert', 'server', 'app.py')
        if os.path.exists(converter_script):
            print(f"🚀 執行 convert：{converter_script}")
            converter_result = subprocess.run(
                [sys.executable, converter_script, converter_input_path],
                capture_output=True, text=True,
                cwd=os.path.dirname(converter_script),
                encoding="utf-8",  # ✅ 防止 cp950 編碼錯誤
                env={**os.environ,
                     "PYTHONIOENCODING": "utf-8",
                     "PYTHONUTF8": "1",
                     "CATEGORY_OVERRIDE": "math_exam"}  # ✅ 固定分類
            )
            print("💬 convert 輸出：", converter_result.stdout)
            print("⚠️ convert 錯誤：", converter_result.stderr)

            # ✅ convert 自動產出 input/output 檔案
            converter_output_path = converter_input_path.replace('.json', '_output.json')
            if os.path.exists(converter_output_path):
                final_output_path = os.path.join(DOWNLOAD_FOLDER, os.path.basename(converter_output_path))
                shutil.copy(converter_output_path, final_output_path)
                print(f"✅ 已搬回最終輸出：{final_output_path}")
            else:
                print("⚠️ 找不到 convert 的輸出檔案")
        else:
            print("❌ 找不到 convert 的 app.py，請確認路徑！")

        # ------------------------------------------------------
        # ✅ 回傳給前端
        # ------------------------------------------------------
        return jsonify({
            'message': '✅ 已完成 test_reducto + 繁體轉換 + convert 處理！',
            'json_filename': os.path.basename(merged_name)
        })

    except Exception as e:
        print("❌ 錯誤：", e)
        return jsonify({'error': f'程式執行錯誤：{e}'})

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
