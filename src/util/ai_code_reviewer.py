from typing import Dict, List, Any
import os
import openai
from openai import OpenAI

import re
import time
from dotenv import load_dotenv
from src.logger import logger

class AICodeReviewer:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com')
        self.client = OpenAI(api_key=self.api_key,base_url=self.api_base)

        # 配置重试参数
        self.max_retries = 3
        self.retry_delay = 2
        
    def review_code_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评审代码变更
        
        Args:
            changes: 代码变更列表
            
        Returns:
            评审结果
        """
        review_results = {
            'summary': [],
            'file_reviews': [],
            'overall_suggestions': []
        }
        
        try:
            # 分析所有变更
            for change in changes:
                if not change.get('diff'):
                    continue
                    
                file_path = change.get('new_path', '')
                file_ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
                
                # 获取语言特定的提示
                language = self._get_language_from_extension(file_ext)
                if not language:
                    continue
                    
                # 分析单个文件
                file_review = self.review_code(
                    code=change['diff'],
                    language=language,
                    file_path=file_path
                )
                
                if file_review['success']:
                    review_results['file_reviews'].append({
                        'file_path': file_path,
                        'review': file_review
                    })
            
            # 生成整体评审总结
            if review_results['file_reviews']:
                overall_review = self._generate_overall_review(review_results['file_reviews'])
                review_results['summary'] = overall_review.get('summary', [])
                review_results['overall_suggestions'] = overall_review.get('suggestions', [])
                
            return review_results
            
        except Exception as e:
            logger.exception("Failed to review code changes")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_language_from_extension(self, ext: str) -> str:
        """根据文件扩展名获取语言"""
        language_map = {
            'java': 'Java',
            'py': 'Python',
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'cpp': 'C++',
            'cs': 'C#',
            'go': 'Go',
            'rb': 'Ruby',
            'php': 'PHP',
            'scala': 'Scala',
            'kt': 'Kotlin',
            'swift': 'Swift',
            'rs': 'Rust'
        }
        return language_map.get(ext, '')
    
    def review_code(self, code: str, language: str = 'java', file_path: str = '') -> Dict[str, Any]:
        """
        使用AI评审代码
        
        Args:
            code: 代码内容
            language: 编程语言
            file_path: 文件路径
            
        Returns:
            评审结果
        """
        try:
            # 处理代码，移除不必要的注释和限制长度
            sanitized_code = self._sanitize_code_for_prompt(code)
            
            # 生成评审提示
            prompt = self._generate_review_prompt(sanitized_code, language, file_path)
            
            # 获取AI响应
            response = self._get_ai_response(prompt)
            
            # 解析响应
            return self._parse_ai_response(response)
            
        except Exception as e:
            logger.exception(f"AI code review failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_language_specific_prompt(self, language: str) -> str:
        """生成语言特定的评审提示"""
        common_prompt = self._generate_review_prompt('', language)
        
        language_specific_prompts = {
            'Java': """
此外，请特别关注以下Java特定的问题：
1. Spring框架最佳实践
2. Java语言特性使用（如Stream API, Optional等）
3. Java命名规范
4. 异常处理方式
5. 并发处理
6. 序列化处理
""",
            'Python': """
此外，请特别关注以下Python特定的问题：
1. Python风格指南(PEP 8)遵循情况
2. Python idioms使用
3. 类型提示的使用
4. 异常处理
5. 包导入顺序
6. 文档字符串规范
""",
            'JavaScript': """
此外，请特别关注以下JavaScript特定的问题：
1. ES6+特性的使用
2. 异步处理方式
3. 内存泄漏风险
4. 类型安全
5. 模块化实践
6. 框架特定最佳实践
"""
        }
        
        return common_prompt + language_specific_prompts.get(language, '')
    
    def _generate_review_prompt(self, code: str, language: str, file_path: str = '') -> str:
        """生成评审提示"""
        base_prompt = f"""
    请作为资深的{language}开发专家，对以下代码进行全面的代码评审。
    请从以下几个方面进行分析和评审：

    1. 代码质量和风格
    - 命名规范（类、方法、变量的命名是否符合规范）
    - 代码格式（缩进、空格、换行等）
    - 代码组织（类和方法的结构）
    - 代码注释的完整性和准确性

    2. 最佳实践
    - 设计模式的使用是否恰当
    - 是否遵循SOLID原则
    - 是否符合语言特定的最佳实践
    - 异常处理是否完善
    - 是否有代码重复

    3. 性能和效率
    - 算法的时间和空间复杂度
    - 资源使用（内存、CPU、IO等）
    - 是否存在性能瓶颈
    - 是否有优化空间

    4. 安全性
    - 输入验证和数据校验
    - 敏感信息处理
    - SQL注入、XSS等安全隐患
    - 权限控制

    5. 可维护性
    - 代码复杂度（圈复杂度）
    - 方法长度和参数数量
    - 依赖管理
    - 测试覆盖
    - 文档完整性

    6. 特定语言检查：
    """
        # 添加语言特定的检查项
        language_specific_checks = {
            'Java': """
        - 是否正确使用了Java 8+特性（Stream API, Optional等）
        - 异常处理是否符合最佳实践
        - 是否考虑了线程安全
        - 是否正确使用了Spring框架特性
        - 是否正确处理了资源关闭
        - 是否使用了合适的集合类型
        - 是否考虑了序列化
        - equals/hashCode是否正确实现
        - 构造函数是否合理
        - 是否避免了内存泄漏""",
                
                'Python': """
        - 是否符合PEP 8规范
        - 是否正确使用了类型提示
        - 是否使用了适当的Python特性（列表推导式、生成器等）
        - 是否正确处理了上下文管理
        - 是否合理使用了装饰器
        - 包导入顺序是否规范
        - 是否避免了全局变量
        - 是否正确处理了编码问题
        - 是否使用了适当的数据结构
        - 是否考虑了Python GIL的影响""",
                
                'JavaScript': """
        - 是否使用了现代JS特性（ES6+）
        - 异步代码是否合理（Promise、async/await）
        - 是否考虑了浏览器兼容性
        - 是否有潜在的内存泄漏
        - 是否正确处理了事件监听器
        - 是否使用了适当的模块化方案
        - 是否考虑了性能优化
        - 是否正确处理了错误边界
        - 是否遵循框架的最佳实践
        - 是否考虑了安全问题（XSS等）""",
                
                'TypeScript': """
        - 类型定义是否准确和完整
        - 是否正确使用了泛型
        - 接口定义是否合理
        - 是否利用了TS的高级特性
        - 是否正确处理了null和undefined
        - 类型断言是否合理
        - 是否使用了适当的工具类型
        - 声明文件是否完整
        - 是否遵循了TSLint规范
        - 是否合理使用了枚举类型""",
                
        }

        if language in language_specific_checks:
            base_prompt += language_specific_checks[language]
        
        base_prompt += """
        请提供详细的评审意见，包括：
        1. 具体的问题描述和位置
        2. 改进建议
        3. 代码示例（如果适用）
        4. 优先级标注（高、中、低）

        代码：
        ```{}{}""".format(language, code)
        # 添加文件特定的上下文
        if file_path:
            file_context = self._get_review_prompt_by_file_type(file_path)
            if file_context:
                base_prompt += f"\n特定文件上下文：\n{file_context}"

        return base_prompt


    def _generate_overall_review(self, file_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成整体评审总结"""
        try:
            # 构建总结提示
            summary_prompt = f"""
请对以下{len(file_reviews)}个文件的代码评审结果进行总结，包括：
1. 主要问题和模式
2. 整体改进建议
3. 优先级排序
4. 可能的重构建议

评审结果：
"""
            for review in file_reviews:
                summary_prompt += f"\n文件: {review['file_path']}\n"
                summary_prompt += review['review']['review_result']
            
            # 获取AI总结
            response = self._get_ai_response(summary_prompt)
            
            return self._parse_ai_response(response)
            
        except Exception as e:
            logger.exception("Failed to generate overall review")
            return {
                'summary': [],
                'suggestions': []
            }

    def _retry_ai_request(self, func, *args, **kwargs):
        """重试AI请求"""
        import time
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except openai.RateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (attempt + 1)
                logger.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {str(e)}")
                raise
            except Exception as e:
                logger.exception("Unexpected error during AI request")
                raise

    def format_review_comment(self, review_results: Dict[str, Any]) -> str:
        """格式化评审评论为Markdown格式"""
        comment_parts = []
        
        # 添加标题
        comment_parts.append("# AI 代码评审报告 🤖\n")
        
        # 添加总体评估
        if review_results.get('summary'):
            comment_parts.append("## 总体评估")
            for summary_item in review_results['summary']:
                comment_parts.append(f"- {summary_item}")
            comment_parts.append("")
            
        # 添加文件级别评审
        if review_results.get('file_reviews'):
            comment_parts.append("## 文件评审详情")
            for file_review in review_results['file_reviews']:
                comment_parts.append(f"\n### 📄 {file_review['file_path']}")
                if file_review['review'].get('suggestions'):
                    for category in file_review['review']['suggestions']:
                        comment_parts.append(f"\n#### {category['category']}")
                        for item in category['items']:
                            comment_parts.append(f"- {item}")
                            
        # 添加整体建议
        if review_results.get('overall_suggestions'):
            comment_parts.append("\n## 整体改进建议")
            for suggestion in review_results['overall_suggestions']:
                comment_parts.append(f"- {suggestion}")
                
        # 添加优先级建议
        comment_parts.append("\n## 优先处理建议")
        priority_issues = self._get_priority_issues(review_results)
        if priority_issues:
            comment_parts.append("\n### 🚨 高优先级")
            for issue in priority_issues.get('high', []):
                comment_parts.append(f"- {issue}")
                
            comment_parts.append("\n### ⚠️ 中优先级")
            for issue in priority_issues.get('medium', []):
                comment_parts.append(f"- {issue}")
                
            comment_parts.append("\n### 💡 建议改进")
            for issue in priority_issues.get('low', []):
                comment_parts.append(f"- {issue}")
        
        # 添加注脚
        comment_parts.append("\n---")
        comment_parts.append("*此评审报告由 AI 辅助生成，如有疑问请人工复核*")
        
        return "\n".join(comment_parts)

    def _get_priority_issues(self, review_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """从评审结果中提取并分类优先级问题"""
        priority_issues = {
            'high': [],
            'medium': [],
            'low': []
        }
        
        # 定义优先级关键词
        priority_keywords = {
            'high': ['安全', '漏洞', '崩溃', '性能问题', '内存泄漏', '并发问题', '死锁'],
            'medium': ['代码重复', '可维护性', '复杂度高', '设计模式', '测试覆盖'],
            'low': ['格式化', '命名', '注释', '文档', '建议', '优化']
        }
        
        # 处理所有文件的评审结果
        for file_review in review_results.get('file_reviews', []):
            if not file_review.get('review', {}).get('suggestions'):
                continue
                
            for category in file_review['review']['suggestions']:
                for item in category['items']:
                    # 根据关键词确定优先级
                    if any(keyword in item for keyword in priority_keywords['high']):
                        priority_issues['high'].append(item)
                    elif any(keyword in item for keyword in priority_keywords['medium']):
                        priority_issues['medium'].append(item)
                    else:
                        priority_issues['low'].append(item)
        
        return priority_issues

    def _sanitize_code_for_prompt(self, code: str) -> str:
        """处理代码以适应提示限制"""
        # 移除注释
        code_lines = []
        in_multi_line_comment = False
        
        for line in code.split('\n'):
            # 处理多行注释
            if '/*' in line:
                in_multi_line_comment = True
                line = line[:line.index('/*')]
            if '*/' in line and in_multi_line_comment:
                in_multi_line_comment = False
                line = line[line.index('*/') + 2:]
            if in_multi_line_comment:
                continue
                
            # 处理单行注释
            if '//' in line:
                line = line[:line.index('//')]
                
            if line.strip():
                code_lines.append(line)
        
        # 限制代码长度
        MAX_LINES = 100
        if len(code_lines) > MAX_LINES:
            code_lines = code_lines[:MAX_LINES]
            code_lines.append("// ... (code truncated for length)")
        
        return '\n'.join(code_lines)

    def _get_review_prompt_by_file_type(self, file_path: str) -> str:
        """根据文件类型获取特定的评审提示"""
        file_ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        
        prompts = {
            'java': """
        关注以下Java特定问题：
        - Spring框架最佳实践
        - Java 8+ 特性使用
        - 并发和线程安全
        - 异常处理
        - 资源管理
        - JVM性能考虑
        """,
                'py': """
        关注以下Python特定问题：
        - PEP 8 规范
        - Python性能优化
        - 类型提示
        - 异步处理
        - 包管理
        - 内存使用
        """,
                'js': """
        关注以下JavaScript特定问题：
        - ES6+特性使用
        - 异步处理
        - 框架最佳实践
        - 浏览器兼容性
        - 性能优化
        - 安全考虑
        """
        }
        
        return prompts.get(file_ext, "")

    def _format_line_comment(self, line_num: int, issues: List[str]) -> str:
        """格式化行级别评论"""
        comment = f"**代码行 {line_num} 评审意见：**\n\n"
        
        # 按类型分类问题
        categorized_issues = {
            '问题': [],
            '建议': [],
            '改进': []
        }
        
        for issue in issues:
            if '问题' in issue or '错误' in issue:
                categorized_issues['问题'].append(issue)
            elif '建议' in issue:
                categorized_issues['建议'].append(issue)
            else:
                categorized_issues['改进'].append(issue)
        
        # 格式化输出
        for category, items in categorized_issues.items():
            if items:
                comment += f"\n{category}:\n"
                for item in items:
                    comment += f"- {item}\n"
        
        return comment

    def _get_ai_response(self, prompt: str) -> str:
        """
        获取AI响应
        
        Args:
            prompt: 提示文本
            
        Returns:
            AI响应文本
            
        Raises:
            Exception: API调用失败时抛出异常
        """
        try:
            # 使用重试机制调用API
            return self._retry_ai_request(self._make_ai_request, prompt)
            
        except openai.APIConnectionError as e:
            logger.error(f"Failed to connect to OpenAI API: {str(e)}")
            raise
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {str(e)}")
            raise
        except openai.APIError as e:
            logger.error(f"API error: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Failed to get AI response: {str(e)}")
            raise

    def _make_ai_request(self, prompt: str) -> str:
        """
        执行OpenAI API请求
        
        Args:
            prompt: 提示文本
            
        Returns:
            AI响应文本
        """
        response =  self.client.chat.completions.create(
            model="claude-3-5-sonnet-20241022",
            messages=[
                {
                    "role": "system",
                    "content": """你是一个资深的代码评审专家，擅长:
    1. 发现代码中的问题和潜在风险
    2. 提供具体的改进建议
    3. 确保代码符合最佳实践
    4. 建议性能优化方案
    5. 识别安全隐患
    请以专业、清晰和建设性的方式提供代码评审意见。"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        return response.choices[0].message.content

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """
        解析AI响应文本
        
        Args:
            response: AI响应文本
            
        Returns:
            解析后的结构化数据
        """
        try:
            # 初始化结果结构
            result = {
                'success': True,
                'review_result': response,
                'suggestions': [],
                'categories': {
                    'code_quality': [],
                    'best_practices': [],
                    'performance': [],
                    'security': [],
                    'maintainability': []
                },
                'priorities': {
                    'high': [],
                    'medium': [],
                    'low': []
                }
            }

            # 分析响应文本
            lines = response.split('\n')
            current_category = None
            current_priority = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查分类标题
                if line.endswith(':') and not line.startswith('-'):
                    current_category = self._determine_category(line[:-1].lower())
                    continue
                    
                # 检查优先级标记
                priority_match = re.search(r'\[(高|中|低)优先级\]', line)
                if priority_match:
                    priority = {
                        '高': 'high',
                        '中': 'medium',
                        '低': 'low'
                    }.get(priority_match.group(1))
                    if priority:
                        current_priority = priority
                        line = line.replace(priority_match.group(0), '').strip()
                        
                # 处理建议内容
                if line.startswith(('-', '•', '*', '+')):
                    suggestion = line[1:].strip()
                    if suggestion:
                        # 添加到总体建议列表
                        result['suggestions'].append(suggestion)
                        
                        # 添加到分类列表
                        if current_category and current_category in result['categories']:
                            result['categories'][current_category].append(suggestion)
                            
                        # 添加到优先级列表
                        if current_priority:
                            result['priorities'][current_priority].append(suggestion)

            # 处理代码示例
            code_examples = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
            if code_examples:
                result['code_examples'] = code_examples
                
            # 提取总结性建议
            summary_match = re.search(r'总结[：:](.*?)(?:\n\n|$)', response, re.DOTALL)
            if summary_match:
                result['summary'] = summary_match.group(1).strip()

            return result
            
        except Exception as e:
            logger.exception(f"Failed to parse AI response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'review_result': response,
                'suggestions': []
            }

    def _determine_category(self, text: str) -> str:
        """
        确定建议类别
        
        Args:
            text: 文本内容
            
        Returns:
            类别名称
        """
        category_keywords = {
            'code_quality': ['代码质量', '代码风格', '命名', '格式'],
            'best_practices': ['最佳实践', '设计模式', 'solid', '原则'],
            'performance': ['性能', '效率', '优化', '复杂度'],
            'security': ['安全', '漏洞', '注入', 'xss'],
            'maintainability': ['可维护性', '复杂度', '测试', '文档']
        }
        
        text = text.lower()
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                return category
                
        return 'code_quality'  # 默认分类
