"""
Security middleware and utilities for google-adk Framework
Provides authentication, authorization, and input validation
"""

import time
import hmac
import hashlib
import secrets
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from aiohttp import web, hdrs
from aiohttp.web_middlewares import middleware
import jwt

from .logging_config import get_logger
from .exceptions import SecurityError, AuthenticationError, AuthorizationError, ValidationError


class SecurityConfig:
    """Security configuration"""
    
    def __init__(self):
        self.jwt_secret = secrets.token_urlsafe(32)
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_hours = 24
        self.api_key_header = "X-API-Key"
        self.rate_limit_per_minute = 60
        self.max_request_size = 1024 * 1024  # 1MB
        self.allowed_origins: Set[str] = {"http://localhost", "https://localhost"}
        self.require_api_key = True
        self.require_jwt = False


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 60, window_minutes: int = 1):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.requests: Dict[str, list] = {}
        self.logger = get_logger("security.rate_limiter")
        
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        now = time.time()
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[client_id] = []
            
        # Check rate limit
        if len(self.requests[client_id]) >= self.max_requests:
            self.logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={"client_id": client_id, "requests_count": len(self.requests[client_id])}
            )
            return False
            
        # Record this request
        self.requests[client_id].append(now)
        return True


class APIKeyManager:
    """Simple API key management"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("security.api_keys")
        
    def generate_api_key(self, client_name: str, permissions: Optional[Set[str]] = None) -> str:
        """Generate a new API key"""
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            "client_name": client_name,
            "permissions": permissions or set(),
            "created_at": datetime.utcnow(),
            "last_used": None,
            "active": True
        }
        
        self.logger.info(
            f"Generated API key for client {client_name}",
            extra={"client_name": client_name, "permissions": list(permissions or [])}
        )
        
        return api_key
        
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return client info"""
        if not api_key or api_key not in self.api_keys:
            return None
            
        key_info = self.api_keys[api_key]
        if not key_info["active"]:
            return None
            
        # Update last used
        key_info["last_used"] = datetime.utcnow()
        
        return key_info
        
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            self.logger.info(f"Revoked API key", extra={"api_key_prefix": api_key[:8]})
            return True
        return False


class JWTManager:
    """JWT token management"""
    
    def __init__(self, secret: str, algorithm: str = "HS256"):
        self.secret = secret
        self.algorithm = algorithm
        self.logger = get_logger("security.jwt")
        
    def generate_token(self, payload: Dict[str, Any], expiry_hours: int = 24) -> str:
        """Generate a JWT token"""
        now = datetime.utcnow()
        payload.update({
            "iat": now,
            "exp": now + timedelta(hours=expiry_hours),
            "iss": "google-adk"
        })
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        
        self.logger.info(
            "Generated JWT token",
            extra={"subject": payload.get("sub"), "expiry_hours": expiry_hours}
        )
        
        return token
        
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token"""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid JWT token: {e}")
            return None


class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_json_size(data: bytes, max_size: int = 1024 * 1024) -> None:
        """Validate JSON payload size"""
        if len(data) > max_size:
            raise ValidationError(
                f"Request payload too large: {len(data)} bytes (max: {max_size})"
            )
            
    @staticmethod
    def validate_content_type(request: web.Request, allowed_types: Set[str] = None) -> None:
        """Validate request content type"""
        if allowed_types is None:
            allowed_types = {"application/json"}
            
        content_type = request.headers.get(hdrs.CONTENT_TYPE, "").split(";")[0].strip()
        
        if content_type not in allowed_types:
            raise ValidationError(
                f"Invalid content type: {content_type}. Allowed: {allowed_types}"
            )
            
    @staticmethod
    def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers"""
        sanitized = {}
        for key, value in headers.items():
            # Remove potentially dangerous characters
            clean_key = "".join(c for c in key if c.isalnum() or c in "-_")
            clean_value = "".join(c for c in value if ord(c) < 127 and c.isprintable())
            sanitized[clean_key] = clean_value
        return sanitized


class SecurityMiddleware:
    """Security middleware for aiohttp applications"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_per_minute)
        self.api_key_manager = APIKeyManager()
        self.jwt_manager = JWTManager(config.jwt_secret, config.jwt_algorithm)
        self.logger = get_logger("security.middleware")
        
        # Generate a default API key for development
        if not config.require_jwt:
            default_key = self.api_key_manager.generate_api_key("default", {"all"})
            self.logger.info(f"Generated default API key: {default_key}")
            
    @middleware
    async def security_middleware(self, request: web.Request, handler: Callable) -> web.Response:
        """Main security middleware"""
        start_time = time.time()
        
        try:
            # Extract client identifier
            client_id = self._get_client_id(request)
            
            # Rate limiting
            if not self.rate_limiter.is_allowed(client_id):
                raise SecurityError("Rate limit exceeded", error_code="RATE_LIMIT_EXCEEDED")
                
            # Validate request size
            if request.content_length and request.content_length > self.config.max_request_size:
                raise ValidationError(f"Request too large: {request.content_length} bytes")
                
            # CORS validation
            await self._validate_cors(request)
            
            # Authentication
            await self._authenticate_request(request)
            
            # Input validation
            await self._validate_input(request)
            
            # Process request
            response = await handler(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Log successful request
            duration = time.time() - start_time
            self.logger.info(
                "Request processed successfully",
                extra={
                    "client_id": client_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            return response
            
        except SecurityError as e:
            self.logger.warning(
                f"Security error: {e.message}",
                extra={
                    "client_id": self._get_client_id(request),
                    "error_code": e.error_code,
                    "path": request.path
                }
            )
            return web.json_response(
                {"error": e.error_code, "message": e.message},
                status=403
            )
            
        except ValidationError as e:
            self.logger.warning(
                f"Validation error: {e.message}",
                extra={"client_id": self._get_client_id(request), "path": request.path}
            )
            return web.json_response(
                {"error": "VALIDATION_ERROR", "message": e.message},
                status=400
            )
            
        except Exception as e:
            self.logger.error(
                f"Unexpected security error: {str(e)}",
                extra={"client_id": self._get_client_id(request), "path": request.path},
                exc_info=True
            )
            return web.json_response(
                {"error": "INTERNAL_ERROR", "message": "Internal security error"},
                status=500
            )
            
    def _get_client_id(self, request: web.Request) -> str:
        """Extract client identifier from request"""
        # Try to get from X-Forwarded-For, then remote address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.remote or "unknown"
        
    async def _validate_cors(self, request: web.Request) -> None:
        """Validate CORS headers"""
        origin = request.headers.get("Origin")
        if origin and origin not in self.config.allowed_origins:
            raise SecurityError(f"Origin not allowed: {origin}", error_code="CORS_ERROR")
            
    async def _authenticate_request(self, request: web.Request) -> None:
        """Authenticate the request"""
        # Skip authentication for health checks
        if request.path == "/mcp/health":
            return
            
        authenticated = False
        
        # Try API key authentication
        if self.config.require_api_key:
            api_key = request.headers.get(self.config.api_key_header)
            if api_key:
                key_info = self.api_key_manager.validate_api_key(api_key)
                if key_info:
                    request["client_info"] = key_info
                    authenticated = True
                    
        # Try JWT authentication
        if self.config.require_jwt and not authenticated:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = self.jwt_manager.validate_token(token)
                if payload:
                    request["jwt_payload"] = payload
                    authenticated = True
                    
        if (self.config.require_api_key or self.config.require_jwt) and not authenticated:
            raise AuthenticationError("Authentication required", error_code="AUTH_REQUIRED")
            
    async def _validate_input(self, request: web.Request) -> None:
        """Validate request input"""
        if request.method in {"POST", "PUT", "PATCH"}:
            # Validate content type
            InputValidator.validate_content_type(request)
            
    def _add_security_headers(self, response: web.Response) -> None:
        """Add security headers to response"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


def create_security_middleware(config: SecurityConfig = None) -> SecurityMiddleware:
    """Create security middleware with configuration"""
    if config is None:
        config = SecurityConfig()
    return SecurityMiddleware(config)