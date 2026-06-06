from fastapi import Request, HTTPException


async def csrf_protect(request: Request) -> bool:
    """Double-submit-cookie CSRF check for state-changing form POSTs.

    The browser sends the token both as the ``csrf_token`` cookie (set by the
    security-headers middleware) and as a hidden ``csrf_token`` form field
    (injected by base.html). A cross-site attacker can do neither, so a match
    proves the request originated from our own page.
    """
    # Safe methods never change state and carry no form body.
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return True
    cookie_token = request.cookies.get("csrf_token")
    form = await request.form()
    form_token = form.get("csrf_token")
    if not cookie_token or not form_token or cookie_token != form_token:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")
    return True
