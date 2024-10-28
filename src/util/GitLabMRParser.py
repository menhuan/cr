from typing import Dict, Any, List
import textwrap
from typing import Dict, Any, List
import re
import json
from urllib.parse import urlparse
import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest, ProjectNote
from dotenv import load_dotenv
import os
from src.logger import logger  # 直接导入配置好的 logger
from typing import Dict, List, Any
from .java_analyzer import JavaCodeAnalyzer
from time import sleep

def pretty_print_json(data: Dict[str, Any], title: str = None) -> None:
    """
    美化输出 JSON 数据
    
    Args:
        data: 要输出的数据字典
        title: 输出的标题（可选）
    """
    if title:
        logger.info(f"\n{title}:")
    logger.info(json.dumps(data, indent=2, ensure_ascii=False))



class GitLabMRParser:
    def __init__(self, gitlab_token: str, gitlab_url: str = "https://gitlab.com"):
        """初始化"""
        self.gl = gitlab.Gitlab(url=gitlab_url, private_token=gitlab_token)
        self.java_analyzer = JavaCodeAnalyzer()  # 初始化Java分析器
        self.ai_reviewer = AICodeReviewer()
    def parse_mr_url(self, url: str) -> Dict[str, str]:
        """
        解析 GitLab MR URL
        
        Args:
            url: GitLab MR URL 如 https://gitlab.com/group/project/-/merge_requests/1
            
        Returns:
            包含解析结果的字典
        """
        logger.debug(f"Parsing MR URL: {url}")
        parsed = urlparse(url)
        pattern = r'/([^/]+)/([^/]+)/-/merge_requests/(\d+)'
        match = re.search(pattern, parsed.path)
        
        if not match:
            error_msg = f"Invalid GitLab MR URL format: {url}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        namespace, project_name, mr_iid = match.groups()
        project_id = f"{namespace}/{project_name}"
        
        result = {
            'base_url': f"{parsed.scheme}://{parsed.netloc}",
            'namespace': namespace,
            'project_name': project_name,
            'project_id': project_id,
            'mr_iid': int(mr_iid)
        }
        logger.debug(f"Parsed MR URL result: {result}")
        return result

    def get_project(self, project_id: str) -> Project:
        """
        获取 GitLab 项目对象
        
        Args:
            project_id: 项目ID或路径（如 'group/project'）
            
        Returns:
            Project 对象
        """
        logger.info(f"Getting project: {project_id}")
        try:
            project = self.gl.projects.get(project_id)
            logger.debug(f"Successfully got project: {project.name}")
            return project
        except gitlab.exceptions.GitlabError as e:
            error_msg = f"Failed to get project {project_id}: {str(e)}"
            logger.error(error_msg)
            raise

    def get_merge_request(self, project: Project, mr_iid: int) -> ProjectMergeRequest:
        """
        获取合并请求对象
        
        Args:
            project: Project 对象
            mr_iid: MR IID
            
        Returns:
            ProjectMergeRequest 对象
        """
        logger.info(f"Getting merge request: {mr_iid} from project: {project.name}")
        try:
            mr = project.mergerequests.get(mr_iid)
            logger.debug(f"Successfully got MR: {mr.title}")
            return mr
        except gitlab.exceptions.GitlabError as e:
            error_msg = f"Failed to get MR {mr_iid}: {str(e)}"
            logger.error(error_msg)
            raise

    def get_mr_changes(self, url: str) -> Dict[str, Any]:
        """
        获取 MR 的变更内容
        
        Args:
            url: GitLab MR URL
            
        Returns:
            包含变更内容的字典
        """
        logger.info(f"Getting MR changes for: {url}")
        try:
            parsed_info = self.parse_mr_url(url)
            project = self.get_project(parsed_info['project_id'])
            mr = self.get_merge_request(project, parsed_info['mr_iid'])
            
            changes = mr.changes()
            
            # 构建更友好的变更信息
            formatted_changes = {
                'id': mr.id,
                'iid': mr.iid,
                'title': mr.title,
                'state': mr.state,
                'created_at': mr.created_at,
                'updated_at': mr.updated_at,
                'source_branch': mr.source_branch,
                'target_branch': mr.target_branch,
                'changes': []
            }
            
            # 处理每个文件的变更
            for change in changes['changes']:
                formatted_changes['changes'].append({
                    'old_path': change.get('old_path'),
                    'new_path': change.get('new_path'),
                    'diff': change.get('diff'),
                    'new_file': change.get('new_file', False),
                    'renamed_file': change.get('renamed_file', False),
                    'deleted_file': change.get('deleted_file', False)
                })
            
            logger.debug(f"Successfully got changes for MR: {mr.title}")
            return formatted_changes
            
        except Exception as e:
            error_msg = f"Failed to get MR changes: {str(e)}"
            logger.error(error_msg)
            raise

    def get_mr_details(self, url: str) -> Dict[str, Any]:
        """
        获取 MR 的详细信息
        
        Args:
            url: GitLab MR URL
            
        Returns:
            包含 MR 详细信息的字典
        """
        logger.info(f"Getting MR details for: {url}")
        try:
            parsed_info = self.parse_mr_url(url)
            project = self.get_project(parsed_info['project_id'])
            mr = self.get_merge_request(project, parsed_info['mr_iid'])
            
            details = {
                'id': mr.id,
                'iid': mr.iid,
                'title': mr.title,
                'description': mr.description,
                'state': mr.state,
                'merged': mr.state == 'merged',
                'merged_at': getattr(mr, 'merged_at', None),
                'created_at': mr.created_at,
                'updated_at': mr.updated_at,
                'source_branch': mr.source_branch,
                'target_branch': mr.target_branch,
                'author': {
                    'id': mr.author['id'],
                    'name': mr.author['name'],
                    'username': mr.author['username']
                },
                'labels': mr.labels,
                'web_url': mr.web_url
            }
            
            logger.debug(f"Successfully got details for MR: {mr.title}")
            return details
            
        except Exception as e:
            error_msg = f"Failed to get MR details: {str(e)}"
            logger.error(error_msg)
            raise
    
        
    def analyze_code_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析代码变更"""
        logger.info("Starting code analysis")
        review_results = {
            'summary': {
                'total_files': len(changes),
                'total_additions': 0,
                'total_deletions': 0,
                'file_types': {}
            },
            'files_analysis': [],
            'java_analysis': {
                'files_analyzed': 0,
                'total_issues': 0,
                'critical_issues': 0,
                'warnings': 0,
                'suggestions': 0,
                'file_results': []
            }
        }

        for change in changes:
            try:
                file_path = change.get('new_path', '')
                if not file_path or not change.get('diff'):
                    continue

                # 基本文件分析
                file_analysis = self._analyze_single_file(change)
                review_results['files_analysis'].append(file_analysis)
                
                # 收集行评论
                if file_analysis.get('line_comments'):
                    review_results['line_comments'][file_path] = file_analysis['line_comments']
                
                # Java特定分析
                if self._is_java_file(file_path):
                    java_analysis = self._analyze_java_file(change)
                    if java_analysis:
                        review_results['java_analysis']['files_analyzed'] += 1
                        # ... 其他 Java 分析统计 ...
                        
                        # 收集 Java 分析产生的行评论
                        if java_analysis.get('line_comments'):
                            if file_path not in review_results['line_comments']:
                                review_results['line_comments'][file_path] = {}
                            review_results['line_comments'][file_path].update(
                                java_analysis['line_comments']
                            )
                
                # 更新统计信息
                if change.get('new_path'):
                    file_ext = change['new_path'].split('.')[-1] if '.' in change['new_path'] else 'no_extension'
                    review_results['summary']['file_types'][file_ext] = \
                        review_results['summary']['file_types'].get(file_ext, 0) + 1

                # 统计变更行数
                if change.get('diff'):
                    additions = len(re.findall(r'^\+[^+]', change['diff'], re.MULTILINE))
                    deletions = len(re.findall(r'^-[^-]', change['diff'], re.MULTILINE))
                    review_results['summary']['total_additions'] += additions
                    review_results['summary']['total_deletions'] += deletions
                    
            except Exception as e:
                logger.exception(f"Error analyzing file: {change.get('new_path', 'unknown file')}")
                
        return review_results
    def _analyze_single_file(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个文件"""
        file_path = change.get('new_path', '')
        file_analysis = {
            'file_path': file_path,
            'change_type': self._determine_change_type(change),
            'issues': [],
            'warnings': [],
            'suggestions': [],
            'line_comments': {}  # 添加行评论收集
        }

        try:
            if change.get('diff'):
                current_line = 0
                
                # 分析diff获取行号
                diff_lines = change['diff'].split('\n')
                for line in diff_lines:
                    if line.startswith('@@'):
                        match = re.search(r'\+(\d+)', line)
                        if match:
                            current_line = int(match.group(1)) - 1
                        continue
                    
                    if line.startswith('+'):
                        current_line += 1
                        # 分析新添加的代码行
                        line_issues = self._analyze_code_line(line[1:], file_path)
                        if line_issues:
                            file_analysis['line_comments'][current_line] = line_issues
                    
                    elif line.startswith(' '):
                        current_line += 1

        except Exception as e:
            logger.exception(f"Error analyzing file: {file_path}")
            file_analysis['issues'].append(f"文件分析错误: {str(e)}")

        return file_analysis

    def _is_java_file(self, file_path: str) -> bool:
        """判断是否是Java文件"""
        return file_path and file_path.endswith('.java')

    def _analyze_java_file(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """分析Java文件"""
        try:
            if not change.get('diff'):
                return None

            file_path = change.get('new_path', '')
            logger.info(f"Analyzing Java file: {file_path}")

            # 从diff中提取新代码
            new_code = '\n'.join(
                line[1:] for line in change['diff'].split('\n')
                if line.startswith('+') and not line.startswith('++')
            )

            if not new_code.strip():
                return None

            # 执行Java代码分析
            analysis_result = self.java_analyzer.analyze_java_file(new_code, file_path)
            
            return {
                'file_path': file_path,
                'issues': analysis_result.get('issues', []),
                'warnings': analysis_result.get('warnings', []),
                'suggestions': analysis_result.get('suggestions', []),
                'metrics': analysis_result.get('metrics', {}),
                'quality_score': self.java_analyzer._calculate_quality_score(analysis_result)
            }

        except Exception as e:
            logger.exception(f"Error in Java analysis for file {change.get('new_path')}")
            return None

    def format_java_review_comment(self, java_analysis: Dict[str, Any]) -> str:
        """格式化Java代码评审评论"""
        comment_parts = []
        comment_parts.append("## Java代码评审结果\n")
        
        # 总体统计
        comment_parts.append("### 📊 总体统计")
        comment_parts.append(f"- 分析文件数: {java_analysis['files_analyzed']}")
        comment_parts.append(f"- 总问题数: {java_analysis['total_issues']}")
        comment_parts.append(f"- 严重问题: {java_analysis['critical_issues']}")
        comment_parts.append(f"- 警告: {java_analysis['warnings']}")
        comment_parts.append(f"- 建议: {java_analysis['suggestions']}\n")
        
        # 文件详细分析
        if java_analysis['file_results']:
            comment_parts.append("### 📝 详细分析")
            for file_result in java_analysis['file_results']:
                comment_parts.append(f"\n#### {file_result['file_path']}")
                comment_parts.append(f"代码质量得分: {file_result['quality_score']}/100")
                
                if file_result['issues']:
                    comment_parts.append("\n❌ **严重问题:**")
                    for issue in file_result['issues']:
                        comment_parts.append(f"- {issue}")
                
                if file_result['warnings']:
                    comment_parts.append("\n⚠️ **警告:**")
                    for warning in file_result['warnings']:
                        comment_parts.append(f"- {warning}")
                
                if file_result['suggestions']:
                    comment_parts.append("\n💡 **建议:**")
                    for suggestion in file_result['suggestions']:
                        comment_parts.append(f"- {suggestion}")
                        
                if file_result.get('metrics'):
                    comment_parts.append("\n📈 **指标:**")
                    for metric, value in file_result['metrics'].items():
                        comment_parts.append(f"- {metric}: {value}")
        
        return '\n'.join(comment_parts)
    
    
    def _format_review_comment(self, review_results: Dict[str, Any]) -> str:
        """
        格式化代码评审评论
        
        Args:
            review_results: 评审结果字典
            
        Returns:
            格式化后的评论字符串
        """
        logger.debug("Formatting review comment")
        comment_parts = []
        
        # 添加标题
        comment_parts.append("# 代码评审报告 📝\n")
        
        # MR基本信息
        if 'mr_info' in review_results:
            comment_parts.append("## 合并请求信息")
            mr_info = review_results['mr_info']
            comment_parts.append(f"- 标题: {mr_info['title']}")
            comment_parts.append(f"- 作者: {mr_info['author']['name']} (@{mr_info['author']['username']})")
            comment_parts.append(f"- 状态: {mr_info['state']}")
            comment_parts.append(f"- 创建时间: {mr_info['created_at']}\n")
        
        # 变更概要
        if 'summary' in review_results:
            comment_parts.append("## 变更概要 📊")
            summary = review_results['summary']
            comment_parts.append(f"- 变更文件总数: {summary['total_files']}")
            comment_parts.append(f"- 新增行数: {summary['total_additions']}")
            comment_parts.append(f"- 删除行数: {summary['total_deletions']}")
            
            # 文件类型统计
            if summary.get('file_types'):
                comment_parts.append("\n### 文件类型分布")
                for file_type, count in summary['file_types'].items():
                    comment_parts.append(f"- {file_type}: {count}个文件")
            comment_parts.append("")
        
        # 文件分析结果
        if review_results.get('files_analysis'):
            comment_parts.append("## 文件分析 🔍")
            for file_analysis in review_results['files_analysis']:
                if file_analysis.get('issues') or file_analysis.get('warnings') or file_analysis.get('suggestions'):
                    comment_parts.append(f"\n### {file_analysis['file_path']}")
                    
                    # 问题
                    if file_analysis.get('issues'):
                        comment_parts.append("\n#### ❌ 问题")
                        for issue in file_analysis['issues']:
                            comment_parts.append(f"- {issue}")
                    
                    # 警告
                    if file_analysis.get('warnings'):
                        comment_parts.append("\n#### ⚠️ 警告")
                        for warning in file_analysis['warnings']:
                            comment_parts.append(f"- {warning}")
                    
                    # 建议
                    if file_analysis.get('suggestions'):
                        comment_parts.append("\n#### 💡 建议")
                        for suggestion in file_analysis['suggestions']:
                            comment_parts.append(f"- {suggestion}")
                            
        # 代码质量指标
        metrics = self._calculate_quality_metrics(review_results)
        if metrics:
            comment_parts.append("\n## 代码质量指标 📈")
            for metric, value in metrics.items():
                comment_parts.append(f"- {metric}: {value}")
        
        # 最佳实践建议
        best_practices = self._get_best_practices_suggestions(review_results)
        if best_practices:
            comment_parts.append("\n## 最佳实践建议 ✨")
            for practice in best_practices:
                comment_parts.append(f"- {practice}")
        
        # 安全性检查
        security_issues = self._check_security_issues(review_results)
        if security_issues:
            comment_parts.append("\n## 安全性检查 🔒")
            for issue in security_issues:
                comment_parts.append(f"- ⚠️ {issue}")
        
        # 总结
        comment_parts.append("\n## 总结建议 📋")
        recommendations = self._generate_recommendations(review_results)
        for rec in recommendations:
            comment_parts.append(f"- {rec}")
            
        # 注脚
        comment_parts.append("\n---")
        comment_parts.append("*此评审报告由自动代码评审工具生成*")
        
        return "\n".join(comment_parts)

    def _calculate_quality_metrics(self, review_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算代码质量指标"""
        metrics = {}
        
        if 'summary' in review_results:
            total_changes = (review_results['summary']['total_additions'] + 
                           review_results['summary']['total_deletions'])
            
            if total_changes > 0:
                # 计算变更规模
                metrics['变更规模'] = '大型变更' if total_changes > 500 else '中型变更' if total_changes > 200 else '小型变更'
                
                # 计算文件影响范围
                files_count = review_results['summary']['total_files']
                metrics['文件影响范围'] = f"{files_count}个文件"
        
        # 计算问题密度
        total_issues = 0
        for file_analysis in review_results.get('files_analysis', []):
            total_issues += (len(file_analysis.get('issues', [])) + 
                           len(file_analysis.get('warnings', [])))
        
        if total_issues > 0:
            metrics['问题密度'] = f"{total_issues}个问题/警告"
            
        return metrics

    def _get_best_practices_suggestions(self, review_results: Dict[str, Any]) -> List[str]:
        """生成最佳实践建议"""
        suggestions = []
        
        # 基于文件分析结果生成建议
        for file_analysis in review_results.get('files_analysis', []):
            for suggestion in file_analysis.get('suggestions', []):
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions

    def _check_security_issues(self, review_results: Dict[str, Any]) -> List[str]:
        """检查安全相关问题"""
        security_issues = []
        
        for file_analysis in review_results.get('files_analysis', []):
            for issue in file_analysis.get('issues', []):
                # 识别安全相关问题
                if any(keyword in issue.lower() for keyword in 
                      ['security', 'secure', 'vulnerability', 'unsafe', 'injection', 'xss', 'csrf']):
                    security_issues.append(issue)
        
        return security_issues

    def _generate_recommendations(self, review_results: Dict[str, Any]) -> List[str]:
        """生成总体建议"""
        recommendations = []
        
        # 基于问题数量生成建议
        total_issues = 0
        total_warnings = 0
        for file_analysis in review_results.get('files_analysis', []):
            total_issues += len(file_analysis.get('issues', []))
            total_warnings += len(file_analysis.get('warnings', []))
        
        if total_issues > 0:
            recommendations.append(f"需要解决的严重问题: {total_issues}个")
        if total_warnings > 0:
            recommendations.append(f"需要关注的警告: {total_warnings}个")
        return recommendations


    def _submit_line_comments(self, mr: ProjectMergeRequest, line_comments: Dict[str, Dict[int, List[str]]]) -> None:
        """
        提交行级别评论
        
        Args:
            mr: MR对象
            line_comments: 行评论字典 {file_path: {line_number: [comments]}}
        """
        try:
            # 配置批处理大小
            BATCH_SIZE = 5
            
            # 按文件处理评论
            for file_path, comments in line_comments.items():
                logger.info(f"Creating comments for file: {file_path}")
                
                if not comments:
                    continue
                    
                # 使用批量处理方法提交评论
                self._create_batch_comments(
                    mr=mr,
                    file_path=file_path,
                    comments=comments,
                    batch_size=BATCH_SIZE
                )
                
                logger.info(f"Successfully submitted comments for {file_path}")
                        
        except Exception as e:
            logger.exception("Failed to submit line comments")
            raise

    def _create_batch_comments(self, mr: ProjectMergeRequest, file_path: str, 
                            comments: Dict[int, List[str]], batch_size: int = 5) -> None:
        """
        批量创建评论
        
        Args:
            mr: MR对象
            file_path: 文件路径
            comments: 评论字典 {line_number: [comments]}
            batch_size: 批次大小
        """
        try:
            # 获取必要的SHA值
            base_sha = mr.diff_refs['base_sha']
            head_sha = mr.diff_refs['head_sha']
            start_sha = mr.diff_refs.get('start_sha', base_sha)
            
            # 将评论按批次处理
            comment_items = list(comments.items())
            total_batches = len(comment_items) // batch_size + (1 if len(comment_items) % batch_size > 0 else 0)
            
            for batch_index in range(total_batches):
                start_idx = batch_index * batch_size
                end_idx = min(start_idx + batch_size, len(comment_items))
                batch = dict(comment_items[start_idx:end_idx])
                
                logger.debug(f"Processing batch {batch_index + 1}/{total_batches} for {file_path}")
                
                # 处理当前批次的评论
                for line_num, issues in batch.items():
                    try:
                        # 格式化评论内容
                        comment_body = self._format_line_comment_body(issues)
                        
                        # 创建评论
                        position_data = {
                            'base_sha': base_sha,
                            'start_sha': start_sha,
                            'head_sha': head_sha,
                            'position_type': 'text',
                            'new_path': file_path,
                            'new_line': line_num,
                            'old_path': file_path,
                            'old_line': None
                        }
                        
                        mr.discussions.create({
                            'body': comment_body,
                            'position': position_data
                        })
                        
                        logger.debug(f"Created comment for line {line_num} in {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to create comment for line {line_num} in {file_path}: {str(e)}")
                
                # 添加延迟以避免触发API限制
                if batch_index < total_batches - 1:  # 如果不是最后一批，添加延迟
                    time.sleep(1)
                
            logger.info(f"Completed submitting {len(comments)} comments for {file_path}")
                
        except Exception as e:
            logger.exception(f"Failed to create batch comments for {file_path}")
            raise

    
    
    def review_mr(self, url: str, batch_size: int = 5) -> Dict[str, Any]:
        """
        执行MR评审
        
        Args:
            url: MR URL
            batch_size: 评论批处理大小
            
        Returns:
            评审结果
        """
        logger.info(f"Starting code review for MR: {url}")
        
        try:
            # 获取MR信息
            parsed_info = self.parse_mr_url(url)
            project = self.get_project(parsed_info['project_id'])
            mr = self.get_merge_request(project, parsed_info['mr_iid'])
            
            # 检查MR状态
            if mr.state not in ['opened', 'reopened']:
                raise ValueError(f"MR is not open for review (state: {mr.state})")
            
            # 获取变更
            changes = self.get_mr_changes(url)
            mr_details = self.get_mr_details(url)
            
            # 分析代码
            review_results = self.analyze_code_changes(changes['changes'])
            
            # 使用 AI 进行代码评审
            ai_review_results = self.ai_reviewer.review_code_changes(changes['changes'])
            if ai_review_results.get('success'):
                review_results['ai_review'] = ai_review_results
        
            
            # 构建结果
            results = {
                'mr_info': {
                    'title': mr_details['title'],
                    'author': mr_details['author'],
                    'state': mr_details['state'],
                    'created_at': mr_details['created_at']
                },
                'changes': changes['changes'],
                **review_results
            }
            
            # 提交评论（使用批处理）
            self._submit_review_results(mr, results, batch_size)
            
            logger.info("Code review completed successfully")
            return results
            
        except Exception as e:
            logger.exception("Failed to complete code review")
            raise


    def _submit_review_results(self, mr: ProjectMergeRequest, review_results: Dict[str, Any], 
                             batch_size: int = 5) -> None:
        """
        提交评审结果
        
        Args:
            mr: MR对象
            review_results: 评审结果
            batch_size: 批处理大小
        """
        try:
            # 添加延迟以避免请求过快
            sleep(1)
            
            # 1. 提交概述评论
            self._submit_overview_comment(mr, review_results)
            
            # 2. 批量提交行评论
            self._submit_line_comments(mr, review_results)
            
            logger.info("Successfully submitted all review comments")
            
        except Exception as e:
            logger.exception("Failed to submit review results")
            raise

    def _submit_overview_comment(self, mr: ProjectMergeRequest, review_results: Dict[str, Any]) -> None:
        """
        提交概述评论
        
        Args:
            mr: MR对象
            review_results: 评审结果
        """
        try:
            # 检查是否需要处理API限制
            self._handle_rate_limits()
            
            # 生成并提交评论
            overview_comment = self._format_review_comment(review_results)
            
             # 2. 如果有 AI 评审结果，添加到评论中
            if 'ai_review' in review_results:
                ai_comment = self.ai_reviewer.format_review_comment(review_results['ai_review'])
                overview_comment = f"{overview_comment}\n\n{ai_comment}"
            
            mr.notes.create({'body': overview_comment})
            
            logger.info("Successfully submitted overview comment")
            
        except Exception as e:
            logger.exception("Failed to submit overview comment")
            raise

    def _submit_line_comments(self, mr: ProjectMergeRequest, review_results: Dict[str, Any]) -> None:
        """提交行级别评论"""
        try:
            # 1. 处理常规分析的行评论
            for file_analysis in review_results.get('files_analysis', []):
                if file_analysis.get('line_comments'):
                    self._create_line_comments(
                        mr, 
                        file_analysis['file_path'],
                        file_analysis['line_comments']
                    )
            
            # 2. 处理 AI 分析的行评论
            if 'ai_review' in review_results:
                for file_review in review_results['ai_review'].get('file_reviews', []):
                    if file_review.get('line_issues'):
                        comments = self.ai_reviewer._format_line_comment(
                            file_review['file_path'],
                            file_review['line_issues']
                        )
                        self._create_line_comments(
                            mr,
                            file_review['file_path'],
                            comments
                        )
                        
        except Exception as e:
            logger.exception("Failed to submit line comments")
            raise
    
    def _create_line_comments(
        self, 
        mr: ProjectMergeRequest, 
        file_path: str, 
        comments: Dict[int, List[str]]
    ) -> None:
        """创建行级别评论"""
        try:
            base_sha = mr.diff_refs['base_sha']
            head_sha = mr.diff_refs['head_sha']
            start_sha = mr.diff_refs.get('start_sha', base_sha)
            
            for line_num, comment_list in comments.items():
                comment_body = "\n".join([
                    f"- {comment}" for comment in comment_list
                ])
                
                position_data = {
                    'base_sha': base_sha,
                    'start_sha': start_sha,
                    'head_sha': head_sha,
                    'position_type': 'text',
                    'new_path': file_path,
                    'new_line': line_num,
                    'old_path': file_path,
                    'old_line': None
                }
                
                mr.discussions.create({
                    'body': comment_body,
                    'position': position_data
                })
                
                logger.debug(f"Created comment for line {line_num} in {file_path}")
                
        except Exception as e:
            logger.exception(f"Failed to create line comments for {file_path}")
            raise    
    
    def _get_file_type_analyzer(self, file_path: str) -> Any:
        """
        获取文件类型对应的分析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            分析器实例
        """
        if file_path.endswith('.java'):
            return self.java_analyzer
        # 可以在这里添加其他类型的分析器
        return None

    def _should_analyze_file(self, file_path: str) -> bool:
        """
        判断是否需要分析该文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否需要分析
        """
        # 排除不需要分析的文件
        exclude_patterns = [
            r'\.git/',
            r'\.idea/',
            r'\.vscode/',
            r'target/',
            r'build/',
            r'dist/',
            r'node_modules/',
            r'\.md$',
            r'\.txt$',
            r'\.log$',
            r'\.lock$',
            r'package-lock\.json$'
        ]
        
        return not any(re.search(pattern, file_path) for pattern in exclude_patterns)

    def _get_diff_context(self, diff: str, line_num: int, context_lines: int = 3) -> str:
        """
        获取diff上下文
        
        Args:
            diff: diff内容
            line_num: 目标行号
            context_lines: 上下文行数
            
        Returns:
            上下文代码
        """
        lines = diff.split('\n')
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        
        context = []
        for i, line in enumerate(lines[start:end], start=start+1):
            prefix = '> ' if i == line_num else '  '
            context.append(f"{prefix}{line}")
            
        return '\n'.join(context)

    

    def _submit_line_comments(self, mr: ProjectMergeRequest, file_path: str, 
                            line_comments: Dict[int, List[str]], change: Dict[str, Any]) -> None:
        """
        提交行级别评论
        
        Args:
            mr: MR 对象
            file_path: 文件路径
            line_comments: 行评论字典
            change: 变更信息
        """
        try:
            logger.info(f"Submitting line comments for file: {file_path}")
            
            # 获取必要的 SHA
            base_sha = mr.diff_refs['base_sha']
            head_sha = mr.diff_refs['head_sha']
            start_sha = mr.diff_refs.get('start_sha', base_sha)
            
            # 对每个有评论的行创建评论
            for line_num, comments in line_comments.items():
                if not comments:
                    continue
                    
                # 格式化评论内容
                comment_body = "🔍 代码评审意见：\n\n" + "\n".join([
                    f"- {comment}" for comment in comments
                ])
                
                try:
                    # 创建行级别评论
                    mr.discussions.create({
                        'body': comment_body,
                        'position': {
                            'base_sha': base_sha,
                            'start_sha': start_sha,
                            'head_sha': head_sha,
                            'position_type': 'text',
                            'new_path': file_path,
                            'new_line': line_num,
                            'old_path': file_path,
                            'old_line': None
                        }
                    })
                    
                    logger.debug(f"Created comment for line {line_num} in {file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to create comment for line {line_num} in {file_path}: {str(e)}")
                    
            logger.info(f"Successfully submitted {len(line_comments)} line comments for {file_path}")
            
        except Exception as e:
            logger.exception(f"Failed to submit line comments for {file_path}")
            raise

    def _collect_line_comments(self, change: Dict[str, Any], review_results: Dict[str, Any]) -> Dict[int, List[str]]:
        """
        收集文件的行级别评论
        
        Args:
            change: 文件变更信息
            review_results: 评审结果
            
        Returns:
            行号到评论的映射字典
        """
        line_comments = {}
        file_path = change.get('new_path', '')
        
        if not file_path or not change.get('diff'):
            return line_comments

        try:
            # 解析 diff 获取行号信息
            diff_lines = change['diff'].split('\n')
            current_line = 0
            
            for line in diff_lines:
                # 处理 diff 头部，更新当前行号
                if line.startswith('@@'):
                    match = re.search(r'\+(\d+)', line)
                    if match:
                        current_line = int(match.group(1)) - 1
                    continue
                
                # 只分析新增或修改的行
                if line.startswith('+'):
                    current_line += 1
                    code_line = line[1:]  # 去掉 '+' 前缀
                    
                    # 根据文件类型进行相应的分析
                    if file_path.endswith('.java'):
                        issues = self.java_analyzer.analyze_java_line(code_line)
                        if issues:
                            line_comments[current_line] = issues
                    
                elif line.startswith(' '):
                    current_line += 1
            
            logger.debug(f"Collected {len(line_comments)} line comments for {file_path}")
            
        except Exception as e:
            logger.exception(f"Error collecting line comments for {file_path}")
        
        return line_comments
    def _validate_position_params(self, mr: ProjectMergeRequest, file_path: str, 
                                line_num: int) -> Dict[str, Any]:
        """
        验证并构建位置参数
        
        Args:
            mr: MR对象
            file_path: 文件路径
            line_num: 行号
            
        Returns:
            位置参数字典
        """
        try:
            # 获取必要的SHA值
            diff_refs = mr.diff_refs
            if not all([diff_refs.get('base_sha'), diff_refs.get('head_sha')]):
                raise ValueError("Missing required diff refs")

            position = {
                'base_sha': diff_refs['base_sha'],
                'start_sha': diff_refs.get('start_sha', diff_refs['base_sha']),
                'head_sha': diff_refs['head_sha'],
                'position_type': 'text',
                'new_path': file_path,
                'new_line': line_num,
                'old_path': file_path,
                'old_line': None
            }

            logger.debug(f"Generated position params for {file_path}:{line_num}")
            return position

        except Exception as e:
            logger.error(f"Failed to validate position params: {str(e)}")
            raise

    def _create_line_comment(self, mr: ProjectMergeRequest, position: Dict[str, Any], 
                           comment: str) -> None:
        """
        创建单个行评论
        
        Args:
            mr: MR对象
            position: 位置参数
            comment: 评论内容
        """
        try:
            discussion = mr.discussions.create({
                'body': comment,
                'position': position
            })
            
            logger.debug(f"Created comment at {position['new_path']}:{position['new_line']}")
            return discussion

        except gitlab.exceptions.GitlabError as e:
            logger.error(f"GitLab API error while creating comment: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while creating comment: {str(e)}")
            raise

    def _format_line_comment(self, issues: List[str]) -> str:
        """
        格式化行评论内容
        
        Args:
            issues: 问题列表
            
        Returns:
            格式化的评论字符串
        """
        comment_parts = ["🔍 代码评审意见：\n"]
        
        # 按严重程度分类
        critical_issues = [i for i in issues if "❌" in i]
        warnings = [i for i in issues if "⚠️" in i]
        suggestions = [i for i in issues if "💡" in i]
        
        if critical_issues:
            comment_parts.append("\n严重问题：")
            comment_parts.extend([f"- {issue}" for issue in critical_issues])
            
        if warnings:
            comment_parts.append("\n警告：")
            comment_parts.extend([f"- {issue}" for issue in warnings])
            
        if suggestions:
            comment_parts.append("\n建议：")
            comment_parts.extend([f"- {issue}" for issue in suggestions])
            
        return "\n".join(comment_parts)

    def _handle_rate_limits(self, retry_count: int = 3, delay: int = 5) -> None:
        """
        处理API速率限制
        
        Args:
            retry_count: 重试次数
            delay: 延迟秒数
        """
        import time

        try:
            # 获取当前用户的请求统计
            # 注意：这需要 API 版本 >= 12.2，且用户需要有足够权限
            user = self.gl.user
            if not user:
                logger.warning("Unable to get user info for rate limit check")
                return

            # 检查响应头中的速率限制信息
            headers = user.manager.gitlab.http_list(user.path)[2]
            remaining = int(headers.get('RateLimit-Remaining', 0))
            reset_time = int(headers.get('RateLimit-Reset', 0))

            if remaining < 10:  # 如果剩余请求数很少
                wait_time = reset_time - int(time.time())
                if wait_time > 0:
                    logger.warning(f"Rate limit almost reached. Waiting {wait_time} seconds...")
                    time.sleep(min(wait_time, 60))  # 最多等待60秒

        except Exception as e:
            logger.warning(f"Failed to check rate limits: {str(e)}")
            # 如果无法检查速率限制，添加一个小的延迟
            time.sleep(1)

    def _chunk_comments(self, comments: List[str], chunk_size: int = 5) -> List[List[str]]:
        """
        将评论分块以避免超过API限制
        
        Args:
            comments: 评论列表
            chunk_size: 每块的大小
            
        Returns:
            评论块列表
        """
        return [comments[i:i + chunk_size] for i in range(0, len(comments), chunk_size)]

    def analyze_code_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析代码变更"""
        logger.info("Starting code analysis")
        review_results = {
            'summary': {
                'total_files': len(changes),
                'total_additions': 0,
                'total_deletions': 0,
                'file_types': {}
            },
            'files_analysis': [],
            'line_comments': {},  # 添加行评论收集
            'java_analysis': {
                'files_analyzed': 0,
                'total_issues': 0,
                'critical_issues': 0,
                'warnings': 0,
                'suggestions': 0,
                'file_results': []
            }
        }

        for change in changes:
            try:
                file_path = change.get('new_path', '')
                if not file_path or not change.get('diff'):
                    continue

                # 基本文件分析
                file_analysis = self._analyze_single_file(change)
                review_results['files_analysis'].append(file_analysis)
                
                # 收集行评论
                if file_analysis.get('line_comments'):
                    review_results['line_comments'][file_path] = file_analysis['line_comments']
                
                # Java特定分析
                if self._is_java_file(file_path):
                    java_analysis = self._analyze_java_file(change)
                    if java_analysis:
                        review_results['java_analysis']['files_analyzed'] += 1
                        # ... 其他 Java 分析统计 ...
                        
                        # 收集 Java 分析产生的行评论
                        if java_analysis.get('line_comments'):
                            if file_path not in review_results['line_comments']:
                                review_results['line_comments'][file_path] = {}
                            review_results['line_comments'][file_path].update(
                                java_analysis['line_comments']
                            )
                
                # 更新统计信息
                if change.get('new_path'):
                    file_ext = change['new_path'].split('.')[-1] if '.' in change['new_path'] else 'no_extension'
                    review_results['summary']['file_types'][file_ext] = \
                        review_results['summary']['file_types'].get(file_ext, 0) + 1

                # 统计变更行数
                if change.get('diff'):
                    additions = len(re.findall(r'^\+[^+]', change['diff'], re.MULTILINE))
                    deletions = len(re.findall(r'^-[^-]', change['diff'], re.MULTILINE))
                    review_results['summary']['total_additions'] += additions
                    review_results['summary']['total_deletions'] += deletions
                    
            except Exception as e:
                logger.exception(f"Error analyzing file: {change.get('new_path', 'unknown file')}")
                
        return review_results

    def _analyze_single_file(self, change: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个文件"""
        file_path = change.get('new_path', '')
        file_analysis = {
            'file_path': file_path,
            'change_type': self._determine_change_type(change),
            'issues': [],
            'warnings': [],
            'suggestions': [],
            'line_comments': {}  # 添加行评论收集
        }

        try:
            if change.get('diff'):
                current_line = 0
                
                # 分析diff获取行号
                diff_lines = change['diff'].split('\n')
                for line in diff_lines:
                    if line.startswith('@@'):
                        match = re.search(r'\+(\d+)', line)
                        if match:
                            current_line = int(match.group(1)) - 1
                        continue
                    
                    if line.startswith('+'):
                        current_line += 1
                        # 分析新添加的代码行
                        line_issues = self._analyze_code_line(line[1:], file_path)
                        if line_issues:
                            file_analysis['line_comments'][current_line] = line_issues
                    
                    elif line.startswith(' '):
                        current_line += 1

        except Exception as e:
            logger.exception(f"Error analyzing file: {file_path}")
            file_analysis['issues'].append(f"文件分析错误: {str(e)}")

        return file_analysis

    def _submit_review_results(self, mr: ProjectMergeRequest, review_results: Dict[str, Any]) -> None:
        """提交评审结果"""
        try:
            # 1. 提交总体评论
            overview_comment = self._format_review_comment(review_results)
            
            # 2. 如果有 AI 评审结果，添加到评论中
            if 'ai_review' in review_results:
                ai_comment = self.ai_reviewer.format_review_comment(review_results['ai_review'])
                overview_comment = f"{overview_comment}\n\n{ai_comment}"
            
            mr.notes.create({'body': overview_comment})
            logger.info("Successfully submitted overview comment")
            
            # 3. 提交行级别评论
            if review_results.get('line_comments'):
                self._submit_line_comments(mr, review_results['line_comments'])
            
            logger.info("Successfully submitted all review comments")
            
        except Exception as e:
            logger.exception("Failed to submit review results")
            raise

    def _submit_line_comments(self, mr: ProjectMergeRequest, line_comments: Dict[str, Dict[int, List[str]]]) -> None:
        """
        提交行级别评论
        
        Args:
            mr: MR对象
            line_comments: 行评论字典 {file_path: {line_number: [comments]}}
        """
        try:
            base_sha = mr.diff_refs['base_sha']
            head_sha = mr.diff_refs['head_sha']
            start_sha = mr.diff_refs.get('start_sha', base_sha)
            
            # 按文件处理评论
            for file_path, comments in line_comments.items():
                logger.info(f"Creating comments for file: {file_path}")
                
                # 按行处理评论
                for line_num, line_issues in comments.items():
                    try:
                        # 格式化评论内容
                        comment_body = self._format_line_comment_body(line_issues)
                        
                        # 创建评论
                        position_data = {
                            'base_sha': base_sha,
                            'start_sha': start_sha,
                            'head_sha': head_sha,
                            'position_type': 'text',
                            'new_path': file_path,
                            'new_line': line_num,
                            'old_path': file_path,
                            'old_line': None
                        }
                        
                        mr.discussions.create({
                            'body': comment_body,
                            'position': position_data
                        })
                        
                        logger.debug(f"Created comment for line {line_num} in {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to create comment for line {line_num} in {file_path}: {str(e)}")
                        
        except Exception as e:
            logger.exception("Failed to submit line comments")
            raise

    def _format_line_comment_body(self, issues: List[str]) -> str:
        """
        格式化行评论内容
        
        Args:
            issues: 问题列表
            
        Returns:
            格式化后的评论内容
        """
        # 按类型对问题进行分类
        categorized_issues = {
            '❌ 严重问题': [],
            '⚠️ 警告': [],
            '💡 建议': []
        }
        
        for issue in issues:
            if any(keyword in issue.lower() for keyword in ['error', 'critical', 'severe', '严重']):
                categorized_issues['❌ 严重问题'].append(issue)
            elif any(keyword in issue.lower() for keyword in ['warning', 'caution', '警告']):
                categorized_issues['⚠️ 警告'].append(issue)
            else:
                categorized_issues['💡 建议'].append(issue)
        
        # 构建评论内容
        comment_parts = ['### 代码评审意见']
        
        for category, category_issues in categorized_issues.items():
            if category_issues:
                comment_parts.append(f"\n**{category}:**")
                for issue in category_issues:
                    comment_parts.append(f"- {issue}")
        
        # 如果有建议的代码示例，添加到评论中
        if any('example' in issue.lower() or '示例' in issue for issue in issues):
            comment_parts.append("\n**💻 参考示例:**")
            for issue in issues:
                if 'example' in issue.lower() or '示例' in issue:
                    comment_parts.append("```java\n" + issue.split('example:')[-1].strip() + "\n```")
        
        return "\n".join(comment_parts)

    def _create_batch_comments(self, mr: ProjectMergeRequest, file_path: str, 
                         comments: Dict[int, List[str]], batch_size: int = 5) -> None:
        """
        批量创建评论
        
        Args:
            mr: MR对象
            file_path: 文件路径
            comments: 评论字典
            batch_size: 批次大小
        """
        try:
            # 获取必要的SHA值
            base_sha = mr.diff_refs['base_sha']
            head_sha = mr.diff_refs['head_sha']
            start_sha = mr.diff_refs.get('start_sha', base_sha)
            
            # 将评论按批次处理
            comment_items = list(comments.items())
            for i in range(0, len(comment_items), batch_size):
                batch = dict(comment_items[i:i + batch_size])
                
                for line_num, issues in batch.items():
                    try:
                        comment_body = self._format_line_comment_body(issues)
                        position_data = {
                            'base_sha': base_sha,
                            'start_sha': start_sha,
                            'head_sha': head_sha,
                            'position_type': 'text',
                            'new_path': file_path,
                            'new_line': line_num,
                            'old_path': file_path,
                            'old_line': None
                        }
                        
                        mr.discussions.create({
                            'body': comment_body,
                            'position': position_data
                        })
                        
                        logger.debug(f"Created comment for line {line_num} in {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to create comment for line {line_num}: {str(e)}")
                
                # 添加延迟以避免触发API限制
                sleep(1)
                
        except Exception as e:
            logger.exception(f"Failed to create batch comments for {file_path}")
            raise

   


def main():
    # 加载环境变量
    load_dotenv()
    
    # 获取配置
    gitlab_token = os.getenv('GITLAB_TOKEN')
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    mr_url = os.getenv('MR_URL','https://gitlab.com/your-group/your-project/-/merge_requests/1')
    
    if not all([gitlab_token, mr_url]):
        logger.error("Missing required environment variables")
        return
    
    try:
        # 初始化解析器并执行评审
        parser = GitLabMRParser(gitlab_token=gitlab_token, gitlab_url=gitlab_url)
        results = parser.review_mr(mr_url)
        
        # 输出结果
        logger.info("Review completed successfully")
        logger.debug(f"Review results: {json.dumps(results, indent=2)}")
        
    except Exception as e:
        logger.exception("Error during code review")
