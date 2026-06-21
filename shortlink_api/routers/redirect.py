from fastapi import APIRouter, Request, HTTPException, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from typing import Optional

from ..services.redirector import handle_redirect, verify_link_password, get_link_by_code
from ..core.config import settings
from ..core.rate_limiter import limiter

router = APIRouter(tags=["redirect"])

PASSWORD_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>密码验证</title>
    <style>
        body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
        .container {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h2 {{ margin-top: 0; color: #333; }}
        input[type="password"] {{ width: 100%; padding: 0.5rem; margin: 0.5rem 0; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ width: 100%; padding: 0.75rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #0056b3; }}
        .error {{ color: red; font-size: 0.875rem; margin-top: 0.5rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>此链接需要密码访问</h2>
        <form method="POST">
            <input type="password" name="password" placeholder="请输入密码" required>
            {error_html}
            <button type="submit">提交</button>
        </form>
    </div>
</body>
</html>
"""


@router.get("/{short_code}")
@limiter.limit(settings.RATE_LIMIT_REDIRECT)
async def redirect_to_original(
    request: Request,
    short_code: str,
    permanent: bool = False,
    shortlink_auth: Optional[str] = Cookie(None),
):
    if len(short_code) > 32:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")
    
    status_code, original_url, password_hash = await handle_redirect(
        short_code, client_ip, user_agent, referer, permanent
    )
    
    if status_code == 404:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    if status_code == 410:
        raise HTTPException(status_code=410, detail="短链接已过期")
    
    if password_hash:
        if shortlink_auth and shortlink_auth == short_code + ":verified":
            return RedirectResponse(url=original_url, status_code=status_code)
        
        error_html = ""
        html = PASSWORD_PAGE_HTML.format(error_html=error_html)
        return HTMLResponse(content=html, status_code=200)
    
    return RedirectResponse(url=original_url, status_code=status_code)


@router.post("/{short_code}/verify-password")
async def verify_password_endpoint(
    request: Request,
    short_code: str,
    password: str = Form(...),
):
    link = await get_link_by_code(short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="短链接不存在")
    
    if not link.get("password_hash"):
        return RedirectResponse(url=f"/{short_code}", status_code=302)
    
    is_valid = await verify_link_password(short_code, password)
    
    if not is_valid:
        error_html = '<div class="error">密码错误，请重试</div>'
        html = PASSWORD_PAGE_HTML.format(error_html=error_html)
        return HTMLResponse(content=html, status_code=401)
    
    response = RedirectResponse(url=f"/{short_code}", status_code=302)
    response.set_cookie(
        key=settings.PASSWORD_COOKIE_NAME,
        value=f"{short_code}:verified",
        max_age=settings.PASSWORD_COOKIE_TTL,
        httponly=True,
        path="/",
    )
    return response
