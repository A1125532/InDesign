import pytest
import json
from pathlib import Path
import sys

sys.path.append('../server')
from app import ExamConverter

class TestExamConverter:
    
    @pytest.fixture
    def converter(self):
        return ExamConverter()
    
    @pytest.fixture
    def sample_input(self):
        with open('../knowledge/math_exam/examples/ex1_input.json', 'r') as f:
            return json.load(f)
    
    def test_category_detection(self, converter, sample_input):
        """測試類別偵測"""
        content = sample_input["result"]["chunks"][0]["content"]
        category = converter.rules.detect_category(content)
        assert category == "math_test"
    
    def test_conversion(self, converter, sample_input):
        """測試完整轉換"""
        output = converter.convert(sample_input)
        
        assert "meta" in output
        assert output["meta"]["category"] == "math_test"
        assert "result" in output
        assert "chunks" in output["result"]
    
    def test_latex_preservation(self, converter, sample_input):
        """測試 LaTeX 保留"""
        output = converter.convert(sample_input)
        content = output["result"]["chunks"][0]["blocks"][0]["content"]
        
        assert "\\(" in content or "\\[" in content
        assert "\\frac" in content or "\\sqrt" in content
    
    def test_question_structure(self, converter, sample_input):
        """測試題目結構"""
        output = converter.convert(sample_input)
        content = output["result"]["chunks"][0]["blocks"][0]["content"]
        
        assert "[problem]" in content
        assert "[option]" in content or "[solution]" in content
