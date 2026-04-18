import re
from typing import Dict, List

class ConversionRules:
    """考卷轉換規則"""
    
    @staticmethod
    def detect_category(content: str) -> str:
        """
        自動偵測考卷類別
        
        Args:
            content: OCR 原始文字
            
        Returns:
            category: 如 'math_test', 'physics_test'
        """
        # 數學關鍵字
        math_keywords = [
            r'\\frac', r'\\sqrt', r'\\leq', r'\\geq',
            '設.*為正數', '求.*最大值', '化簡', '數對'
        ]
        
        # 物理關鍵字（未來擴充）
        physics_keywords = [
            '牛頓', '力學', '電磁', '波動'
        ]
        
        math_score = sum(1 for kw in math_keywords if re.search(kw, content))
        
        if math_score >= 3:
            return "math_exam"
        
        return "unknown"
    
    @staticmethod
    def extract_questions(content: str) -> List[Dict]:
        """
        提取題目結構
        
        Returns:
            [
                {
                    "number": 1,
                    "problem": "題目內容",
                    "options": ["(A)...", "(B)..."],
                    "solution": "解答過程"
                }
            ]
        """
        questions = []
        
        # 正則：匹配題號（1. 2. 3. 等）
        pattern = r'(\d+)\.\s*(.+?)(?=\d+\.|$)'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            num = int(match.group(1))
            body = match.group(2).strip()
            
            # 分離選項
            options = re.findall(r'\([A-E]\)[^\(]+', body)
            
            # 分離解答（通常在「題意」「解」「答案」後）
            solution_match = re.search(r'(題意|解：|答案)[：:](.+)', body, re.DOTALL)
            solution = solution_match.group(2).strip() if solution_match else ""
            
            # 移除解答後的題幹
            problem = re.sub(r'(題意|解：|答案)[：:].*', '', body, flags=re.DOTALL).strip()
            
            questions.append({
                "number": num,
                "problem": problem,
                "options": options,
                "solution": solution
            })
        
        return questions
    
    @staticmethod
    def format_with_tags(question: Dict) -> str:
        """
        加上 [problem] [option] [solution] 標籤
        """
        output = f"[problem]{question['number']}. {question['problem']}"
        
        if question['options']:
            output += "\r[option] " + " ".join(question['options'])
        
        if question['solution']:
            output += f"\r[solution] {question['solution']}"
        
        return output
