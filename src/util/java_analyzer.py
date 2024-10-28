from typing import Dict, List, Any
import re
from src.logger import logger

class JavaCodeAnalyzer:
    """Java代码分析器"""

    def __init__(self):
        # Java代码规范常量
        logger.info("Initializing Java code analyzer")
        self.rules = JavaAnalysisRules().get_all_rules()
        self.MAX_LINE_LENGTH = self.rules.get('code_structure',{}).get('max_line_length')
        self.MAX_METHOD_LENGTH = self.rules.get('code_structure',{}).get('max_method_length')
        self.MAX_CLASS_LENGTH = self.rules.get('code_structure',{}).get('max_class_length')
        self.MAX_PARAMETERS = self.rules.get('code_structure',{}).get('max_parameters')
        self.MAX_COMPLEXITY = self.rules.get('code_structure',{}).get('max_complexity')
        self.DESIGN_VIOLATIONS = self.rules.get('design_violations',{})


    def analyze_java_file(self, content: str, file_path: str) -> Dict[str, Any]:
    
        """分析Java文件"""
        logger.info(f"Analyzing Java file: {file_path}")
        
        analysis = {
            'file_path': file_path,
            'issues': [],
            'warnings': [],
            'suggestions': [],
            'metrics': {
                'total_lines': 0,
                'code_lines': 0,
                'comment_lines': 0,
                'blank_lines': 0,
                'methods_count': 0,
                'classes_count': 0,
                'complexity': 0
            }
        }
        
        try:
            # 基本分析
            self._analyze_basic_metrics(content, analysis)
            
            # 代码规范检查
            self._check_code_style(content, analysis)
            
            # 设计规范检查
            self._check_design_patterns(content, analysis)
            
            # OOP规范检查
            self._check_oop_principles(content, analysis)
            
            # 性能检查
            self._check_performance(content, analysis)
            
            #todo 安全性检查
            self._check_security(content, analysis)
            
            self._check_common_mistakes(content, analysis)
            
        except Exception as e:
            logger.exception(f"Error analyzing Java file {file_path}")
            analysis['issues'].append(f"分析错误: {str(e)}")
            
        return analysis
       
    def analyze_java_line(self, line: str) -> List[str]:
        """
        分析单行Java代码
        
        Args:
            line: 代码行
            
        Returns:
            问题列表
        """
        issues = []
        
        # 获取所有Java分析规则
        rules = self.rules
        
        try:
            # 1. 命名规范检查
            if 'naming_conventions' in rules:
                for name_type, pattern in rules['naming_conventions'].items():
                    if self._check_naming_convention(line, name_type, pattern):
                        issues.append(f"💡 {name_type}命名不符合规范")

            # 2. 代码规范检查
            if 'code_structure' in rules:
                code_issues = self._check_code_structure(line, rules['code_structure'])
                issues.extend(code_issues)

            # 3. 最佳实践检查
            if 'best_practices' in rules:
                for practice in rules['best_practices']:
                    if re.search(practice['pattern'], line):
                        issues.append(f"✨ {practice['message']}")

            # 4. 安全检查
            if 'security_checks' in rules:
                for check in rules['security_checks']:
                    if re.search(check['pattern'], line):
                        issues.append(f"🔒 {check['message']}")

            # 5. 性能检查
            if 'performance_checks' in rules:
                for check in rules['performance_checks']:
                    if re.search(check['pattern'], line):
                        issues.append(f"⚡ {check['message']}")

            # 6. 常见错误检查
            if 'common_mistakes' in rules:
                for mistake in rules['common_mistakes']:
                    if re.search(mistake['pattern'], line):
                        issues.append(f"⚠️ {mistake['message']}")

            logger.debug(f"Found {len(issues)} issues in line: {line[:50]}...")
            
        except Exception as e:
            logger.exception(f"Error analyzing Java line: {line[:50]}...")
            
        return issues
    
    def _analyze_basic_metrics(self, content: str, analysis: Dict[str, Any]) -> None:
        """分析基本指标"""
        lines = content.split('\n')
        analysis['metrics']['total_lines'] = len(lines)

        for line in lines:
            line = line.strip()
            if not line:
                analysis['metrics']['blank_lines'] += 1
            elif line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                analysis['metrics']['comment_lines'] += 1
            else:
                analysis['metrics']['code_lines'] += 1

        # 统计方法数量
        analysis['metrics']['methods_count'] = len(re.findall(
            r'(?:public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*\{',
            content
        ))

        # 统计类数量
        analysis['metrics']['classes_count'] = len(re.findall(r'class\s+\w+', content))

    def _check_code_style(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查代码风格"""
        # 检查命名规范
        for type_name, pattern in self.rules.get("naming_conventions").items():
            matches = re.finditer(pattern, content)
            for match in matches:
                name = match.group(1)
                if type_name == 'class' and not name[0].isupper():
                    analysis['issues'].append(f"类名 '{name}' 应该以大写字母开头")
                elif type_name == 'method' and not name[0].islower():
                    analysis['issues'].append(f"方法名 '{name}' 应该以小写字母开头")
                elif type_name == 'constant' and not name.isupper():
                    analysis['issues'].append(f"常量 '{name}' 应该全部大写")
                elif type_name == 'variable' and not name[0].islower():
                    analysis['issues'].append(f"变量名 '{name}' 应该以小写字母开头")

        # 检查行长度
        for line_num, line in enumerate(content.split('\n'), 1):
            if len(line.strip()) > self.rules.get('code_structure',{}).get('max_line_length'):
                analysis['warnings'].append(f"第 {line_num} 行超过 {self.rules.get('code_structure',{}).get('max_line_length')} 个字符")

        # 检查方法参数数量
        method_params = re.finditer(r'(?:public|private|protected)\s+\w+\s+\w+\s*\(([^)]*)\)', content)
        for match in method_params:
            params = match.group(1).split(',')
            if len(params) > self.rules.get('code_structure',{}).get('max_parameters') :
                analysis['warnings'].append(f"方法参数数量({len(params)})超过最大建议值({self.rules.get('code_structure',{}).get('max_parameters')})")

    def _check_naming_convention(self, line: str, name_type: str, pattern: str) -> bool:
        """
        检查命名规范
        
        Args:
            line: 代码行
            name_type: 命名类型
            pattern: 规范模式
            
        Returns:
            是否违反规范
        """
        patterns = self.rules.get("naming_conventions")
        
        if name_type not in patterns:
            return False
            
        match = re.search(patterns[name_type], line)
        if match:
            name = match.group(1)
            return not bool(re.match(pattern, name))
            
        return False

    def _check_code_structure(self, line: str, rules: Dict[str, int]) -> List[str]:
        """
        检查代码结构
        
        Args:
            line: 代码行
            rules: 结构规则
            
        Returns:
            问题列表
        """
        issues = []
        
        # 检查行长度
        if len(line.strip()) > rules.get('max_line_length', 120):
            issues.append(f"📏 行长度超过{rules.get('max_line_length', 120)}个字符")

        # 检查方法参数
        if 'max_parameters' in rules:
            method_match = re.search(r'\([^)]*\)', line)
            if method_match:
                params = method_match.group(0).strip('()').split(',')
                if len(params) > rules['max_parameters']:
                    issues.append(f"📎 方法参数数量超过{rules['max_parameters']}个")

        # 检查缩进
        indent = len(line) - len(line.lstrip())
        if indent % 4 != 0:
            issues.append("➡️ 缩进应该是4的倍数")

        # 检查空格
        if re.search(r'\s+$', line):
            issues.append("❌ 行尾有多余空格")

        if re.search(r'if\(|for\(|while\(', line):
            issues.append("📝 控制语句的括号前应有空格")

        return issues
    def _check_design_patterns(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查设计模式相关问题"""
        # 检查单例模式实现
        if re.search(self.DESIGN_VIOLATIONS['singleton_pattern'], content):
            analysis['suggestions'].append("发现单例模式实现，建议考虑依赖注入")

        # 检查大类（上帝类）
        if re.search(self.DESIGN_VIOLATIONS['god_class'], content):
            analysis['issues'].append("类可能过于庞大，建议拆分为多个小类")

        # 检查紧耦合
        new_instances = re.finditer(r'new\s+([A-Z]\w+)\(', content)
        concrete_classes = set()
        for match in new_instances:
            concrete_classes.add(match.group(1))
        if len(concrete_classes) > 5:
            analysis['warnings'].append("发现多处直接实例化具体类，建议使用工厂模式或依赖注入")
            
        # 检查接口实现
        if not re.search(r'implements\s+\w+', content) and re.search(r'class\s+\w+', content):
            analysis['suggestions'].append("类没有实现任何接口，建议考虑面向接口编程")

    def _check_oop_principles(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查面向对象原则"""
        # 检查封装性
        fields = re.finditer(r'(private|protected|public)\s+\w+\s+\w+\s*;', content)
        public_fields = 0
        for field in fields:
            if field.group(1) == 'public':
                public_fields += 1
        if public_fields > 0:
            analysis['warnings'].append(f"发现{public_fields}个公共字段，违反封装原则")

        # 检查继承深度
        inheritance_chain = re.findall(r'extends\s+\w+', content)
        if len(inheritance_chain) > 2:
            analysis['warnings'].append("继承层次过深，建议使用组合替代继承")

        # 检查方法重写
        if re.search(r'@Override\s+public\s+\w+\s+\w+\s*\(', content):
            methods = re.finditer(r'@Override\s+public\s+(\w+)\s+(\w+)\s*\(([^)]*)\)', content)
            for method in methods:
                params = method.group(3).split(',')
                if len(params) > 3:
                    analysis['suggestions'].append(f"重写方法 {method.group(2)} 参数过多，考虑简化")

    def _check_performance(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查性能相关问题"""
        # 检查字符串连接
        string_concat = re.finditer(r'("[^"]*"\s*\+\s*)+', content)
        for match in string_concat:
            analysis['suggestions'].append("使用字符串拼接，建议使用StringBuilder")

        # 检查集合初始化
        if re.search(r'new\s+(Array|Hash|Tree|Linked)(List|Map|Set)\s*\(\s*\)', content):
            analysis['suggestions'].append("集合初始化时建议指定初始容量")

        # 检查异常处理
        empty_catches = re.findall(r'catch\s*\([^)]+\)\s*{\s*}', content)
        if empty_catches:
            analysis['issues'].append("发现空的catch块，建议至少记录日志")

        # 检查资源关闭
        if re.search(r'new\s+(FileInputStream|FileOutputStream|Connection|Statement)', content):
            if not re.search(r'try\s*\([^)]+\)', content):
                analysis['warnings'].append("使用了IO/数据库资源，建议使用try-with-resources确保资源关闭")

    def _check_java_specific_rules(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查Java特定规则"""
        # 检查equals和hashCode
        has_equals = bool(re.search(r'@Override\s+public\s+boolean\s+equals\s*\(', content))
        has_hashcode = bool(re.search(r'@Override\s+public\s+int\s+hashCode\s*\(', content))
        if has_equals != has_hashcode:
            analysis['issues'].append("equals和hashCode方法应该成对出现")

        # 检查序列化
        if re.search(r'implements\s+Serializable', content):
            if not re.search(r'static\s+final\s+long\s+serialVersionUID\s*=', content):
                analysis['warnings'].append("实现Serializable接口的类应该定义serialVersionUID")

        # 检查线程安全
        if re.search(r'implements\s+Runnable|extends\s+Thread', content):
            synchronized_count = len(re.findall(r'synchronized', content))
            if synchronized_count == 0:
                analysis['suggestions'].append("多线程类没有同步机制，请确认是否需要同步")
            elif synchronized_count > 5:
                analysis['warnings'].append("过多的synchronized使用，考虑使用Lock或并发集合")

    def _check_code_complexity(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查代码复杂度"""
        # 计算循环嵌套深度
        max_loop_depth = 0
        current_depth = 0
        for line in content.split('\n'):
            if re.search(r'\b(for|while)\b.*\{', line):
                current_depth += 1
                max_loop_depth = max(max_loop_depth, current_depth)
            if re.search(r'\}', line):
                current_depth = max(0, current_depth - 1)
        
        if max_loop_depth > self.rules.get('code_structure').get("max_loop_depth"):
            analysis['warnings'].append(f"存在{max_loop_depth}层循环嵌套，建议重构")

        # 计算条件复杂度
        conditions = re.findall(r'\b(if|else|for|while|case)\b', content)
        if len(conditions) > self.rules.get('code_structure').get('max_complexity'):
            analysis['warnings'].append("代码复杂度过高，建议拆分方法")

    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """生成分析报告"""
        report = []
        report.append("# Java代码评审报告")
        report.append("\n## 基础指标")
        report.append(f"- 总行数: {analysis['metrics']['total_lines']}")
        report.append(f"- 代码行数: {analysis['metrics']['code_lines']}")
        report.append(f"- 注释行数: {analysis['metrics']['comment_lines']}")
        report.append(f"- 空白行数: {analysis['metrics']['blank_lines']}")
        report.append(f"- 方法数量: {analysis['metrics']['methods_count']}")
        report.append(f"- 类数量: {analysis['metrics']['classes_count']}")
        
        if analysis['issues']:
            report.append("\n## 严重问题")
            for issue in analysis['issues']:
                report.append(f"- ❌ {issue}")
                
        if analysis['warnings']:
            report.append("\n## 警告")
            for warning in analysis['warnings']:
                report.append(f"- ⚠️ {warning}")
                
        if analysis['suggestions']:
            report.append("\n## 建议")
            for suggestion in analysis['suggestions']:
                report.append(f"- 💡 {suggestion}")
                
        report.append("\n## 代码质量检查结果")
        quality_score = self._calculate_quality_score(analysis)
        report.append(f"- 代码质量得分: {quality_score}/100")
        
        return "\n".join(report)

    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> int:
        """计算代码质量得分"""
        score = 100
        
        # 根据问题数量扣分
        score -= len(analysis['issues']) * 10
        score -= len(analysis['warnings']) * 5
        score -= len(analysis['suggestions']) * 2
        
        # 根据复杂度扣分
        methods_count = analysis['metrics']['methods_count']
        if methods_count > 20:
            score -= (methods_count - 20) * 2
            
        # 根据代码行数扣分
        code_lines = analysis['metrics']['code_lines']
        if code_lines > 500:
            score -= (code_lines - 500) // 100 * 5
            
        # 确保分数在0-100之间
        return max(0, min(100, score))

    def _check_common_mistakes(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查常见错误"""
        common_mistakes = self.rules.get('common_mistakes', [])
        
        for mistake in common_mistakes:
            if re.search(mistake['pattern'], content):
                analysis['warnings'].append(mistake['message'])

    def _check_security(self, content: str, analysis: Dict[str, Any]) -> None:
        """检查安全性问题"""
        security_checks = self.rules.get('security_checks', [])
        
        for check in security_checks:
            if re.search(check['pattern'], content):
                analysis['issues'].append(check['message'])

class JavaAnalysisRules:
    """Java代码分析规则集"""
         # Java代码规范常量
    MAX_LINE_LENGTH = 120
    MAX_METHOD_LENGTH = 60
    MAX_CLASS_LENGTH = 1000
    MAX_PARAMETERS = 5
    MAX_COMPLEXITY = 15
        
    @staticmethod
    def get_naming_convention() ->Dict[str, str]:
        """检查命名规范"""
        patterns = {
            'class': r'^[A-Z][a-zA-Z0-9]*$',
            'interface': r'^[A-Z][a-zA-Z0-9]*$',
            'method': r'^[a-z][a-zA-Z0-9]*$',
            'variable': r'^[a-z][a-zA-Z0-9]*$',
            'constant': r'^[A-Z][A-Z0-9_]*$',
            'package': r'^[a-z]+(\.[a-z][a-z0-9]*)*$'
        }
        return patterns

    @staticmethod
    def get_code_smells() -> Dict[str, str]:
        """获取代码异味规则"""
        return {
            'long_method': {
                'pattern': r'(?:public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}',
                'message': "方法过长，建议拆分"
            },
            'large_class': {
                'pattern': r'class\s+\w+\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}',
                'message': "类过大，建议拆分"
            },
            'switch_statement': {
                'pattern': r'switch\s*\([^)]*\)\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}',
                'message': "switch语句过多，考虑使用策略模式"
            },
            'primitive_obsession': {
                'pattern': r'(String|int|long|boolean|double|float)\[\]',
                'message': "过度使用基本类型数组，考虑使用对象"
            }
        }

    @staticmethod
    def get_best_practices() -> List[Dict[str, str]]:
        """获取最佳实践规则"""
        return [
            {
                'name': "使用StringBuilder",
                'pattern': r'String\s+\w+\s*=\s*"[^"]*"\s*\+',
                'message': "字符串拼接建议使用StringBuilder"
            },
            {
                'name': "避免空catch块",
                'pattern': r'catch\s*\([^)]+\)\s*{\s*}',
                'message': "空的catch块，至少应该记录日志"
            },
            {
                'name': "资源关闭",
                'pattern': r'new\s+(FileInputStream|FileOutputStream|Connection)',
                'message': "使用try-with-resources确保资源关闭"
            },
            {
                'name': "避免System.out",
                'pattern': r'System\.(out|err)\.',
                'message': "避免使用System.out，应使用日志框架"
            }
        ]

    @staticmethod
    def get_clean_code_principles() -> List[Dict[str, Any]]:
        """获取整洁代码原则"""
        return [
            {
                'principle': "单一职责原则(SRP)",
                'checks': [
                    {
                        'pattern': r'class.*\{.*((public|private)\s+\w+\s+\w+\s*\([^)]*\).*){10,}',
                        'message': "类中方法过多，可能违反单一职责原则"
                    }
                ]
            },
            {
                'principle': "开放封闭原则(OCP)",
                'checks': [
                    {
                        'pattern': r'instanceof\s+\w+.*instanceof\s+\w+',
                        'message': "多个instanceof检查，考虑使用多态"
                    }
                ]
            },
            {
                'principle': "Liskov替换原则(LSP)",
                'checks': [
                    {
                        'pattern': r'@Override.*throw\s+new\s+UnsupportedOperationException',
                        'message': "重写方法抛出不支持异常，违反LSP"
                    }
                ]
            },
            {
                'principle': "接口隔离原则(ISP)",
                'checks': [
                    {
                        'pattern': r'interface.*\{.*(public|private)\s+\w+\s+\w+\s*\([^)]*\).*\}',
                        'message': "接口方法过多，考虑拆分"
                    }
                ]
            },
            {
                'principle': "依赖倒置原则(DIP)",
                'checks': [
                    {
                        'pattern': r'new\s+[A-Z]\w+\([^)]*\)',
                        'message': "直接实例化具体类，考虑依赖注入"
                    }
                ]
            }
        ]
    @staticmethod
    def get_security_checks() -> List[Dict[str, Any]]:
        """获取安全性检查规则"""
        return [
            {
                'name': "SQL注入检查",
                'pattern': r'Statement\s*\.\s*execute\s*\(\s*.*\+\s*.*\)',
                'message': "可能存在SQL注入风险，建议使用PreparedStatement",
                'severity': "HIGH"
            },
            {
                'name': "XSS检查",
                'pattern': r'response\s*\.\s*getWriter\s*\(\s*\)\s*\.\s*print\s*\(\s*.*\)',
                'message': "直接输出未经处理的数据可能导致XSS攻击",
                'severity': "HIGH"
            },
            {
                'name': "敏感数据处理",
                'pattern': r'password|secret|key|token',
                'message': "请确保敏感数据已经过加密处理",
                'severity': "HIGH"
            },
            {
                'name': "不安全的加密",
                'pattern': r'MD5|DES',
                'message': "使用了不安全的加密算法，建议使用更强的加密方式",
                'severity': "MEDIUM"
            }
        ]

    @staticmethod
    def get_performance_checks() -> List[Dict[str, Any]]:
        """获取性能相关检查规则"""
        return [
            {
                'name': "循环中的字符串连接",
                'pattern': r'for\s*\(.*\)\s*\{[^}]*\+[^}]*\}',
                'message': "循环中进行字符串连接，建议使用StringBuilder",
                'severity': "MEDIUM"
            },
            {
                'name': "集合初始容量",
                'pattern': r'new\s+(ArrayList|HashMap|HashSet)\s*\(\s*\)',
                'message': "建议指定集合初始容量以避免扩容开销",
                'severity': "LOW"
            },
            {
                'name': "IO操作效率",
                'pattern': r'new\s+(FileInputStream|FileOutputStream)',
                'message': "考虑使用BufferedInputStream/BufferedOutputStream提高IO效率",
                'severity': "MEDIUM"
            },
            {
                'name': "线程池使用",
                'pattern': r'new\s+Thread\s*\(',
                'message': "直接创建线程，建议使用线程池",
                'severity': "MEDIUM"
            }
        ]

    @staticmethod
    def get_test_related_checks() -> List[Dict[str, Any]]:
        """获取测试相关的检查规则"""
        return [
            {
                'name': "测试方法命名",
                'pattern': r'@Test\s+public\s+void\s+test\w*\s*\(',
                'message': "测试方法名应该清晰描述测试目的",
                'severity': "LOW"
            },
            {
                'name': "测试断言",
                'pattern': r'@Test(?![^{]*Assert\.)',
                'message': "测试方法中没有发现断言语句",
                'severity': "MEDIUM"
            },
            {
                'name': "测试覆盖",
                'pattern': r'public\s+class\s+\w+(?![^{]*@Test)',
                'message': "公共类可能缺少对应的测试类",
                'severity': "MEDIUM"
            }
        ]

    @staticmethod
    def check_spring_framework_practices(content: str) -> List[Dict[str, Any]]:
        """检查Spring Framework相关最佳实践"""
        issues = []
        
        # 检查依赖注入方式
        if re.search(r'@Autowired\s+private', content):
            issues.append({
                'type': 'spring',
                'message': "建议使用构造器注入替代字段注入",
                'severity': "MEDIUM"
            })
        
        # 检查事务使用
        if re.search(r'@Transactional(?![^{]*propagation)', content):
            issues.append({
                'type': 'spring',
                'message': "建议明确指定事务传播行为",
                'severity': "LOW"
            })
        
        # 检查异常处理
        if re.search(r'@ControllerAdvice|@ExceptionHandler', content) and \
           not re.search(r'ResponseEntityExceptionHandler', content):
            issues.append({
                'type': 'spring',
                'message': "建议继承ResponseEntityExceptionHandler统一处理异常",
                'severity': "LOW"
            })
        
        # 检查配置类
        if re.search(r'@Configuration\s+public\s+class', content) and \
           not re.search(r'@ConfigurationProperties', content):
            issues.append({
                'type': 'spring',
                'message': "考虑使用@ConfigurationProperties进行配置绑定",
                'severity': "LOW"
            })
        
        return issues

    @staticmethod
    def check_architecture_patterns(content: str) -> List[Dict[str, Any]]:
        """检查架构模式相关问题"""
        issues = []
        
        # 检查分层架构
        if re.search(r'@Service.*@Repository|@Controller.*@Repository', content):
            issues.append({
                'type': 'architecture',
                'message': "违反分层架构原则，不应跨层直接访问",
                'severity': "HIGH"
            })
        
        # 检查领域模型
        if re.search(r'class.*implements\s+Serializable', content) and \
           re.search(r'@Entity|@Table', content):
            issues.append({
                'type': 'architecture',
                'message': "不建议将JPA实体直接用作DTO",
                'severity': "MEDIUM"
            })
        
        # 检查业务逻辑位置
        if re.search(r'@Controller.*if.*for.*while', content):
            issues.append({
                'type': 'architecture',
                'message': "控制器中包含过多业务逻辑，建议移至Service层",
                'severity': "HIGH"
            })
        
        return issues

    @staticmethod
    def get_common_mistakes_patterns() -> List[Dict[str, str]]:
        """获取常见错误模式"""
        return [
            {
                'pattern': r'null\s*==\s*\w+',
                'message': "建议使用 Objects.isNull() 或将null放在equals()的参数位置"
            },
            {
                'pattern': r'\.equals\s*\(\s*null\s*\)',
                'message': "调用equals时未进行null检查"
            },
            {
                'pattern': r'catch\s*\([^)]*Exception\s*[^)]*\)\s*{\s*return\s+null\s*;}',
                'message': "捕获异常后直接返回null，建议抛出业务异常"
            },
            {
                'pattern': r'if\s*\([^)]*\)\s*{\s*return\s+true\s*;\s*}\s*return\s+false\s*;',
                'message': "可以直接返回条件表达式"
            },
            {
                'pattern': r'for\s*\([^)]*\)\s*{\s*if\s*\([^)]*\)\s*{\s*continue;\s*}\s*}',
                'message': "可以将continue条件取反以减少嵌套"
            }
        ]

    @staticmethod
    def check_concurrent_issues( content: str) -> List[Dict[str, Any]]:
        """检查并发相关问题"""
        issues = []
        
        # 检查线程安全问题
        thread_safety_checks = {
            'synchronized_collections': {
                'pattern': r'Vector|Hashtable',
                'message': "使用过时的线程安全集合，建议使用并发集合类"
            },
            'date_usage': {
                'pattern': r'new\s+Date\(\)',
                'message': "Date类不是线程安全的，建议使用LocalDateTime"
            },
            'singleton_dcl': {
                'pattern': r'private\s+static\s+volatile\s+\w+\s+instance',
                'message': "双重检查锁定模式可能存在问题，建议使用枚举或内部类实现单例"
            },
            'thread_local_usage': {
                'pattern': r'static\s+\w+\s+\w+\s*=\s*new\s+ThreadLocal',
                'message': "确保ThreadLocal变量在不需要时及时移除"
            }
        }
        
        for check in thread_safety_checks.values():
            if re.search(check['pattern'], content):
                issues.append({
                    'type': 'concurrent',
                    'message': check['message'],
                    'severity': "HIGH"
                })
        
        return issues

    @staticmethod
    def check_stream_api_usage( content: str) -> List[Dict[str, str]]:
        """检查Stream API使用情况"""
        suggestions = []
        
        # 检查可以使用Stream API的场景
        stream_patterns = [
            {
                'pattern': r'for\s*\([^)]*\)\s*{\s*if\s*\([^)]*\)\s*{\s*\w+\.add\(',
                'message': "可以使用Stream.filter()和collect()替代for循环过滤"
            },
            {
                'pattern': r'for\s*\([^)]*\)\s*{\s*\w+\.add\(\w+\.get\w+\(\)\)',
                'message': "可以使用Stream.map()替代for循环转换"
            },
            {
                'pattern': r'Collections\.sort\(\w+',
                'message': "可以使用Stream.sorted()进行排序"
            }
        ]
        
        for pattern in stream_patterns:
            if re.search(pattern['pattern'], content):
                suggestions.append(pattern['message'])
                
        return suggestions

    @staticmethod
    def check_api_design( content: str) -> List[Dict[str, Any]]:
        """检查API设计相关问题"""
        issues = []
        
        # REST API设计检查
        if re.search(r'@RestController|@Controller', content):
            # 检查URL命名
            if re.search(r'@RequestMapping\s*\(\s*"/[A-Z]', content):
                issues.append({
                    'type': 'api_design',
                    'message': "REST API URL应使用小写字母",
                    'severity': "LOW"
                })
            
            # 检查HTTP方法使用
            if re.search(r'@RequestMapping\s*\([^)]*method\s*=\s*RequestMethod\.GET[^)]*\)[^{]*private', content):
                issues.append({
                    'type': 'api_design',
                    'message': "API方法不应该是private的",
                    'severity': "MEDIUM"
                })
            
            # 检查响应封装
            if not re.search(r'ResponseEntity|Result|Response', content):
                issues.append({
                    'type': 'api_design',
                    'message': "建议使用统一的响应封装类",
                    'severity': "LOW"
                })

        # 接口设计检查
        if re.search(r'interface\s+\w+\s*{', content):
            # 检查接口方法数量
            methods = re.findall(r'(?:public|private|protected)?\s*\w+\s+\w+\s*\([^)]*\)\s*;', content)
            if len(methods) > 5:
                issues.append({
                    'type': 'api_design',
                    'message': f"接口包含{len(methods)}个方法，建议拆分",
                    'severity': "MEDIUM"
                })
        
        return issues
    @staticmethod
    def get_design_violations()-> Dict[str, str]:
        """设计模式违规"""
        return {
            'singleton_pattern': r'private\s+static\s+\w+\s+instance',
            'god_class': r'class.*\{.*((public|private)\s+\w+\s+\w+\s*\([^)]*\).*){20,}',
            'tight_coupling': r'new\s+[A-Z]\w+\(',
        }
        
    def get_all_rules(self) -> Dict[str, Any]:
        """获取所有检查规则"""
        return {
            'naming_conventions': self.get_naming_convention(),
            'code_structure': {
                'max_line_length': 120,
                'max_method_length': 60,
                'max_class_length': 1000,
                'max_parameters': 5,
                'max_complexity': 15,
                'max_loop_depth': 3,
            },
            'best_practices': self.get_best_practices(),
            'security_checks': self.get_security_checks(),
            'performance_checks': self.get_performance_checks(),
            'test_checks': self.get_test_related_checks(),
            'clean_code': self.get_clean_code_principles(),
            'common_mistakes': self.get_common_mistakes_patterns(),
            'design_violations': self.get_design_violations(),
        }
