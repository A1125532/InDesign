from typing import List, Dict


class BBoxGenerator:
    """為數學考卷生成標準化的 bbox"""
    
    # 標準 bbox 模板（固定寬高）
    STANDARD_BBOX = {
        "left": 0.045,
        "width": 0.86,
        "height": 0.09
    }
    
    # 每題的 top 間距
    TOP_INCREMENT = 0.1
    
    # 每頁題數
    QUESTIONS_PER_PAGE = 5
    
    # 第一題的起始 top
    FIRST_QUESTION_TOP = 0.07
    
    @classmethod
    def generate_bbox(cls, question_number: int) -> Dict:
        """
        根據題號生成 bbox
        
        Args:
            question_number: 題號（1, 2, 3...）
            
        Returns:
            完整的 bbox 字典
        """
        # 計算頁碼（從 1 開始）
        page = ((question_number - 1) // cls.QUESTIONS_PER_PAGE) + 1
        
        # 計算該頁的第幾題（0-4）
        question_in_page = (question_number - 1) % cls.QUESTIONS_PER_PAGE
        
        # 計算 top 值
        top = cls.FIRST_QUESTION_TOP + (question_in_page * cls.TOP_INCREMENT)
        
        return {
            "left": cls.STANDARD_BBOX["left"],
            "top": round(top, 2),
            "width": cls.STANDARD_BBOX["width"],
            "height": cls.STANDARD_BBOX["height"],
            "page": page
        }
    
    @classmethod
    def generate_blocks_with_bbox(cls, questions: List[Dict]) -> List[Dict]:
        """
        為題目列表生成帶 bbox 的 blocks
        
        Args:
            questions: [{"number": 1, "content": "[problem]..."}, ...]
            
        Returns:
            [{"type": "Text", "bbox": {...}, "content": "..."}, ...]
        """
        blocks = []
        
        for q in questions:
            bbox = cls.generate_bbox(q["number"])
            
            blocks.append({
                "type": "Text",
                "bbox": bbox,
                "content": q["content"]
            })
        
        return blocks
    
    @classmethod
    def organize_by_page(cls, blocks: List[Dict]) -> List[Dict]:
        """
        將 blocks 按頁碼組織成 chunks
        
        Args:
            blocks: 所有 blocks
            
        Returns:
            [{"blocks": [...]}, {"blocks": [...]}, ...]  # 每個元素代表一頁
        """
        # 按頁碼分組
        pages: Dict[int, List[Dict]] = {}
        for block in blocks:
            page = block["bbox"]["page"]
            if page not in pages:
                pages[page] = []
            pages[page].append(block)
        
        # 轉換成 chunks 格式
        chunks: List[Dict] = []
        for page_num in sorted(pages.keys()):
            chunks.append({
                "blocks": pages[page_num]
            })
        
        return chunks
    
    
if __name__ == "__main__":
    import json
    
    print("測試生成 10 題的 bbox：\n")
    
    for i in range(1, 11):
        bbox = BBoxGenerator.generate_bbox(i)
        print(f"題 {i}: page={bbox['page']}, top={bbox['top']}")
    
    print("\n" + "="*60)
    print("測試完整流程：\n")
    
    questions = [
        {"number": 1, "content": "[problem]1. 第一題..."},
        {"number": 2, "content": "[problem]2. 第二題..."},
        {"number": 3, "content": "[problem]3. 第三題..."},
        {"number": 6, "content": "[problem]6. 第六題..."},
    ]
    
    blocks = BBoxGenerator.generate_blocks_with_bbox(questions)
    chunks = BBoxGenerator.organize_by_page(blocks)
    
    result = {"result": {"chunks": chunks}}
    print(json.dumps(result, ensure_ascii=False, indent=2))


