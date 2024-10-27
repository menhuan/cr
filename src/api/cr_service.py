from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import os
from src.util.GitLabMRParser import GitLabMRParser

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="Code Review API",
    description="自动代码评审 API 服务",
    version="1.0.0"
)

# 请求模型
class CodeReviewRequest(BaseModel):
    mr_url: HttpUrl
    submit_comment: bool = False
    line_comments: bool = False

# 响应模型
class CodeReviewResponse(BaseModel):
    status: str
    message: str
    review_results: Optional[Dict[str, Any]] = None

@app.post("/api/v1/code-review", response_model=CodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    """
    对 GitLab MR 进行代码评审
    
    - **mr_url**: GitLab MR URL
    - **submit_comment**: 是否提交总评论
    - **line_comments**: 是否提交行评论
    """
    try:
        # 获取环境变量
        gitlab_token = os.getenv('GITLAB_TOKEN')
        gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
        
        if not gitlab_token:
            raise HTTPException(
                status_code=500,
                detail="GitLab token not configured"
            )
        
        # 初始化 GitLab 解析器
        parser = GitLabMRParser(
            gitlab_token=gitlab_token,
            gitlab_url=gitlab_url
        )
        
        # 执行代码评审
        review_results = parser.review_mr(
            url=str(request.mr_url),
            batch_size=5
        )
        
        return CodeReviewResponse(
            status="success",
            message="Code review completed successfully",
            review_results=review_results
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MR URL: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during code review: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}

def start_server():
    """启动服务器"""
    uvicorn.run(
        "src.api.cr_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    start_server()
