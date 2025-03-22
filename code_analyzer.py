# code_analyzer.py
import ast
from typing import Tuple, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeAnalyzer:
    @staticmethod
    def analyze_code_structure(code: str) -> Tuple[List[str], List[str], Dict]:
        """
        Analyze Python code and extract functions, classes, and their relationships.
        
        Args:
            code (str): Python source code
            
        Returns:
            Tuple containing lists of function names, class names, and their relationships
        """
        try:
            tree = ast.parse(code)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            # Analyze relationships and dependencies
            relationships = {
                'class_methods': {},
                'function_calls': [],
                'imports': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    relationships['class_methods'][node.name] = methods
                elif isinstance(node, ast.Import):
                    relationships['imports'].extend(n.name for n in node.names)
                    
            return functions, classes, relationships
        except Exception as e:
            logger.error(f"Error analyzing code: {str(e)}")
            return [], [], {}