from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class BBox(BaseModel):
    """邊界框座標"""
    left: float
    top: float
    width: float
    height: float
    page: int

class Block(BaseModel):
    """內容區塊"""
    type: Literal["Text", "List Item", "Section Header", "Key Value"]
    bbox: BBox
    content: str
    image_url: Optional[str] = None
    confidence: Optional[str] = None

class Chunk(BaseModel):
    """文件片段"""
    blocks: List[Block]

class Meta(BaseModel):
    """元資料 - 用於分類"""
    category: str = Field(..., description="考卷類別，如 math_test, physics_test")

class ExamOutput(BaseModel):
    """標準化輸出格式"""
    meta: Meta
    result: dict = Field(..., description="包含 chunks 的結果")

class ExamInput(BaseModel):
    """輸入格式（來自 Reducto OCR）"""
    job_id: str
    result: dict
