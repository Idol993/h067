from fastapi import APIRouter, Request, HTTPException, Form, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from typing import Optional

from ..services.redirector import (
    handle_redirect,
    handle_redirect_without_stats,
    verify_link_password,
    get_link_by_code,
    record_visit_after_password_verified,
)
from ..core.config import settings
from ..core.rate_limiter import limiter
from ..core.security import generate_signed_cookie, verify_signed_cookie

router = APIRouter(tags=["redirect"])

PASSWORD_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>密码验证</title>
    <style>
        body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
        .container {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 360px; }}
        h2 {{ margin-top: 0; color: #333; text-align: center; }}
        .info {{ color: #666; font-size: 0.875rem; margin-bottom: 1rem; text-align: center; }}
        input[type="password"] {{ width: 100%; padding: 0.75rem; margin: 0.5rem 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 1rem; }}
        button {{ width: 100%; padding: 0.75rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; margin-top: 0.5rem; }}
        button:hover {{ background: #0056b3; }}
        .error {{ color: #dc3545; font-size: 0.875rem; margin-top: 0.5rem; padding: 0.5rem; background: #f8d7da; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🔒 密码访问</h2>
        <p class="info">此短链接受密码保护</p>
        <form method="POST" action="/{short_code}">
            <input type="password" name="password" placeholder="请输入访问密码" required autofocus>
            {error_html}
            <button type="submit">验证并访问</button>
        </form>
    </div>
</body>
</html>
"""


def _render_password_page(short_code: str, error_message: str = "") -> str:
    error_html = f'<div class="error">{error_message}</div>' if error_message else ""
    return PASSWORD_PAGE_HTML.format(short_code=short_code, error_html=error_html)


def _get_client_info(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    referer = request.headers.get("referer", "")
    return client_ip, user_agent, referer


@router.get("/{short_code}")
@limiter.limit(settings.RATE_LIMIT_REDIRECT)
async def redirect_to_original_get(
    request: Request,
    short_code: str,
    permanent: bool = False,
    shortlink_auth: Optional[str] = Cookie(None),
):
    if len(short_code) > 32:
        raise HTTPException(status_code=404, detail="短链接不存在")

    client_ip, user_agent, referer = _get_client_info(request)

    status_code, original_url, password_hash = await handle_redirect_without_stats(
        short_code, permanent
    )

    if status_code == 404:
        raise HTTPException(status_code=404, detail="短链接不存在")

    if status_code == 410:
        raise HTTPException(status_code=410, detail="短链接已过期")

    if password_hash:
        cookie_valid, cookie_sc = verify_signed_cookie(shortlink_auth or "")
        if cookie_valid and cookie_sc == short_code:
            await record_visit_after_password_verified(
                short_code, client_ip, user_agent, referer
            )
            return RedirectResponse(url=original_url, status_code=status_code)

        html = _render_password_page(short_code)
        return HTMLResponse(content=html, status_code=200)

    await record_visit_after_password_verified(
        short_code, client_ip, user_agent, referer
    )
    return RedirectResponse(url=original_url, status_code=status_code)


@router.post("/{short_code}")
@limiter.limit(settings.RATE_LIMIT_REDIRECT)
async def redirect_to_original_post(
    request: Request,
    short_code: str,
    password: str = Form(...),
    permanent: bool = False,
):
    if len(short_code) > 32:
        raise HTTPException(status_code=404, detail="短链接不存在")

    client_ip, user_agent, referer = _get_client_info(request)

    status_code, original_url, password_hash = await handle_redirect_without_stats(
        short_code, permanent
    )

    if status_code == 404:
        raise HTTPException(status_code=404, detail="短链接不存在")

    if status_code == 410:
        raise HTTPException(status_code=410, detail="短链接已过期")

    if password_hash:
        is_valid = await verify_link_password(short_code, password)
        if not is_valid:
            html = _render_password_page(short_code, "密码错误，请重试")
            return HTMLResponse(content=html, status_code=200)

        await record_visit_after_password_verified(
            short_code, client_ip, user_agent, referer
        )
        signed_cookie = generate_signed_cookie(short_code)
        response = RedirectResponse(url=original_url, status_code=303)
        response.set_cookie(
            key=settings.PASSWORD_COOKIE_NAME,
            value=signed_cookie,
            max_age=settings.PASSWORD_COOKIE_TTL,
            httponly=True,
            path="/",
            samesite="lax",
        )
        return response

    await record_visit_after_password_verified(
        short_code, client_ip, user_agent, referer
    )
    return RedirectResponse(url=original_url, status_code=303)
