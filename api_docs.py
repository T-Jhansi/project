# api_docs.py
import ast
import inspect
from typing import Dict, List, Any
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    path: str
    method: str
    description: str
    parameters: List[Dict[str, Any]]
    response: Dict[str, Any]
    auth_required: bool

class APIDocumentationGenerator:
    def __init__(self):
        self.endpoints = []
    
    def parse_fastapi_app(self, code: str):
        """Parse FastAPI application code to extract API endpoints"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._parse_router_class(node)
                elif isinstance(node, ast.FunctionDef):
                    self._parse_endpoint(node)
        except Exception as e:
            logger.error(f"Error parsing FastAPI app: {str(e)}")
    
    def _parse_router_class(self, node: ast.ClassDef):
        """Parse FastAPI router class"""
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self._parse_endpoint(item, class_name=node.name)
    
    def _parse_endpoint(self, node: ast.FunctionDef, class_name: str = None):
        """Parse individual endpoint function"""
        try:
            # Extract path from decorators
            path = None
            method = None
            auth_required = False
            
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if hasattr(decorator.func, 'attr'):
                        method = decorator.func.attr.lower()
                        # Extract path from args or keywords
                        for arg in decorator.args:
                            if isinstance(arg, ast.Str):
                                path = arg.s
                        for kw in decorator.keywords:
                            if kw.arg == 'path':
                                path = kw.value.s
                    elif isinstance(decorator.func, ast.Name):
                        if decorator.func.id == 'requires_auth':
                            auth_required = True
            
            if path and method:
                # Parse docstring
                docstring = ast.get_docstring(node)
                description = self._parse_docstring(docstring) if docstring else ""
                
                # Parse parameters
                parameters = []
                for arg in node.args.args[1:]:  # Skip self/cls
                    param_type = None
                    if arg.annotation:
                        param_type = self._get_type_hint(arg.annotation)
                    parameters.append({
                        'name': arg.arg,
                        'type': param_type,
                        'required': True  # Could be enhanced by checking defaults
                    })
                
                # Parse return type
                response = {}
                if node.returns:
                    response['type'] = self._get_type_hint(node.returns)
                
                # Create endpoint
                endpoint = APIEndpoint(
                    path=path,
                    method=method,
                    description=description,
                    parameters=parameters,
                    response=response,
                    auth_required=auth_required
                )
                
                self.endpoints.append(endpoint)
        except Exception as e:
            logger.error(f"Error parsing endpoint: {str(e)}")
    
    def _parse_docstring(self, docstring: str) -> Dict[str, str]:
        """Parse docstring to extract structured information"""
        sections = {
            'description': '',
            'parameters': {},
            'returns': '',
            'raises': []
        }
        
        current_section = 'description'
        lines = docstring.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('parameters:'):
                current_section = 'parameters'
            elif line.lower().startswith('returns:'):
                current_section = 'returns'
            elif line.lower().startswith('raises:'):
                current_section = 'raises'
            elif line:
                if current_section == 'description':
                    sections['description'] += line + ' '
                elif current_section == 'parameters':
                    param_match = re.match(r'\s*(\w+)\s*:\s*(.+)', line)
                    if param_match:
                        sections['parameters'][param_match.group(1)] = param_match.group(2)
                elif current_section == 'returns':
                    sections['returns'] += line + ' '
                elif current_section == 'raises':
                    sections['raises'].append(line)
        
        return sections
    
    def _get_type_hint(self, node: ast.AST) -> str:
        """Convert AST type annotation to string representation"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            value = self._get_type_hint(node.value)
            slice_value = self._get_type_hint(node.slice)
            return f"{value}[{slice_value}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "Any"
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI specification"""
        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': 'API Documentation',
                'version': '1.0.0'
            },
            'paths': {}
        }
        
        for endpoint in self.endpoints:
            if endpoint.path not in spec['paths']:
                spec['paths'][endpoint.path] = {}
            
            spec['paths'][endpoint.path][endpoint.method] = {
                'summary': endpoint.description.get('description', ''),
                'parameters': [
                    {
                        'name': param['name'],
                        'in': 'path' if '{' + param['name'] + '}' in endpoint.path else 'query',
                        'required': param['required'],
                        'schema': {
                            'type': param['type'].lower() if param['type'] else 'string'
                        }
                    }
                    for param in endpoint.parameters
                ],
                'responses': {
                    '200': {
                        'description': 'Successful response',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': endpoint.response.get('type', 'object').lower()
                                }
                            }
                        }
                    }
                }
            }
            
            if endpoint.auth_required:
                spec['paths'][endpoint.path][endpoint.method]['security'] = [
                    {'bearerAuth': []}
                ]
        
        return spec
    
    def generate_markdown_docs(self) -> str:
        """Generate Markdown documentation"""
        docs = ["# API Documentation\n\n"]
        
        # Group endpoints by path
        grouped_endpoints = {}
        for endpoint in self.endpoints:
            if endpoint.path not in grouped_endpoints:
                grouped_endpoints[endpoint.path] = []
            grouped_endpoints[endpoint.path].append(endpoint)
        
        # Generate documentation for each path
        for path, endpoints in grouped_endpoints.items():
            docs.append(f"## {path}\n")
            
            for endpoint in endpoints:
                docs.append(f"### {endpoint.method.upper()}\n")
                docs.append(f"{endpoint.description.get('description', '')}\n")
                
                if endpoint.auth_required:
                    docs.append("**Requires Authentication**\n")
                
                if endpoint.parameters:
                    docs.append("\n#### Parameters\n")
                    docs.append("| Name | Type | Required | Description |")
                    docs.append("|------|------|----------|-------------|")
                    for param in endpoint.parameters:
                        desc = endpoint.description.get('parameters', {}).get(param['name'], '')
                        docs.append(
                            f"| {param['name']} | {param['type']} | "
                            f"{'Yes' if param['required'] else 'No'} | {desc} |"
                        )
                
                if endpoint.response:
                    docs.append("\n#### Response\n")
                    docs.append(f"Type: {endpoint.response.get('type', 'object')}\n")
                    if 'returns' in endpoint.description:
                        docs.append(f"Description: {endpoint.description['returns']}\n")
                
                if 'raises' in endpoint.description and endpoint.description['raises']:
                    docs.append("\n#### Errors\n")
                    for error in endpoint.description['raises']:
                        docs.append(f"- {error}\n")
                
                docs.append("\n---\n")
        
        return "\n".join(docs)
    
    def analyze_api_code(self, code: str) -> Dict[str, Any]:
        """Analyze API code and return comprehensive analysis"""
        try:
            self.parse_fastapi_app(code)
            
            return {
                'endpoints_count': len(self.endpoints),
                'auth_required_count': sum(1 for e in self.endpoints if e.auth_required),
                'methods_distribution': self._get_methods_distribution(),
                'openapi_spec': self.generate_openapi_spec(),
                'markdown_docs': self.generate_markdown_docs()
            }
        except Exception as e:
            logger.error(f"Error analyzing API code: {str(e)}")
            return {}
    
    def _get_methods_distribution(self) -> Dict[str, int]:
        """Get distribution of HTTP methods across endpoints"""
        distribution = {}
        for endpoint in self.endpoints:
            method = endpoint.method.upper()
            distribution[method] = distribution.get(method, 0) + 1
        return distribution