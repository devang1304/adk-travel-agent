"""
MCP Protocol Implementation
Handles Model Context Protocol communication between agents
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web

from .messages import (
    MCPMessage, RequestMessage, ResponseMessage, NotificationMessage, ErrorMessage,
    MessageType, create_response, create_notification
)


class MCPProtocol:
    """Core MCP protocol implementation"""
    
    def __init__(self, agent_name: str, host: str = "localhost", port: int = 8888):
        self.agent_name = agent_name
        self.host = host
        self.port = port
        
        # Message handling
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        
        # Connection management
        self.is_connected = False
        self.session: Optional[aiohttp.ClientSession] = None
        self.server: Optional[web.Application] = None
        
        # Logging
        self.logger = logging.getLogger(f"MCP.{agent_name}")
        
    async def start(self):
        """Start the MCP protocol server"""
        if self.is_connected:
            return
            
        # Create HTTP session for outbound requests
        self.session = aiohttp.ClientSession()
        
        # Start HTTP server for inbound messages
        await self._start_server()
        
        self.is_connected = True
        self.logger.info(f"MCP protocol started for {self.agent_name} on {self.host}:{self.port}")
        
    async def stop(self):
        """Stop the MCP protocol"""
        if not self.is_connected:
            return
            
        self.is_connected = False
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            
        self.logger.info(f"MCP protocol stopped for {self.agent_name}")
        
    async def _start_server(self):
        """Start the HTTP server for receiving messages"""
        self.server = web.Application()
        self.server.router.add_post("/mcp/message", self._handle_incoming_message)
        self.server.router.add_get("/mcp/health", self._handle_health_check)
        
        # Start server (in a real implementation, this would be more robust)
        self.logger.info(f"MCP server listening on {self.host}:{self.port}")
        
    async def _handle_incoming_message(self, request: web.Request) -> web.Response:
        """Handle incoming MCP messages via HTTP"""
        try:
            data = await request.json()
            message = self._parse_message(data)
            
            if message:
                await self._process_message(message)
                return web.Response(status=200, text="OK")
            else:
                return web.Response(status=400, text="Invalid message format")
                
        except Exception as e:
            self.logger.error(f"Error handling incoming message: {e}")
            return web.Response(status=500, text=str(e))
            
    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "agent": self.agent_name,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def _parse_message(self, data: Dict[str, Any]) -> Optional[MCPMessage]:
        """Parse incoming message data"""
        try:
            message_type = data.get("type")
            
            if message_type == MessageType.REQUEST:
                return RequestMessage(**data)
            elif message_type == MessageType.RESPONSE:
                return ResponseMessage(**data)
            elif message_type == MessageType.NOTIFICATION:
                return NotificationMessage(**data)
            elif message_type == MessageType.ERROR:
                return ErrorMessage(**data)
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing message: {e}")
            return None
            
    async def _process_message(self, message: MCPMessage):
        """Process an incoming message"""
        if isinstance(message, RequestMessage):
            await self._handle_request(message)
        elif isinstance(message, ResponseMessage):
            await self._handle_response(message)
        elif isinstance(message, NotificationMessage):
            await self._handle_notification(message)
        elif isinstance(message, ErrorMessage):
            await self._handle_error(message)
            
    async def _handle_request(self, request: RequestMessage):
        """Handle incoming request messages"""
        try:
            # Find handler for the method
            handler = self.message_handlers.get(request.method)
            if not handler:
                # Send error response
                error_response = create_response(
                    request, 
                    success=False, 
                    error=f"No handler for method: {request.method}"
                )
                await self.send_message(error_response)
                return
                
            # Execute handler
            result = await handler(request.params)
            
            # Send success response
            success_response = create_response(request, success=True, result=result)
            await self.send_message(success_response)
            
        except Exception as e:
            self.logger.error(f"Error handling request {request.method}: {e}")
            error_response = create_response(request, success=False, error=str(e))
            await self.send_message(error_response)
            
    async def _handle_response(self, response: ResponseMessage):
        """Handle incoming response messages"""
        # Find pending request
        future = self.pending_requests.pop(response.request_id, None)
        if future and not future.done():
            future.set_result(response)
            
    async def _handle_notification(self, notification: NotificationMessage):
        """Handle incoming notification messages"""
        # Notify subscribers
        subscribers = self.subscribers.get(notification.event, [])
        for subscriber in subscribers:
            try:
                await subscriber(notification.data)
            except Exception as e:
                self.logger.error(f"Error in notification subscriber: {e}")
                
    async def _handle_error(self, error: ErrorMessage):
        """Handle incoming error messages"""
        self.logger.error(f"Received error: {error.error_code} - {error.error_message}")
        
    def register_handler(self, method: str, handler: Callable):
        """Register a message handler for a specific method"""
        self.message_handlers[method] = handler
        self.logger.info(f"Registered handler for method: {method}")
        
    def subscribe(self, event: str, callback: Callable):
        """Subscribe to notification events"""
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(callback)
        self.logger.info(f"Subscribed to event: {event}")
        
    async def send_message(self, message: MCPMessage, target_agent: str = None) -> bool:
        """Send a message to another agent"""
        if not self.is_connected:
            self.logger.error("Cannot send message: MCP protocol not connected")
            return False
            
        try:
            # Determine target endpoint
            target_url = self._get_agent_endpoint(target_agent or message.recipient)
            
            # Serialize message
            message_data = message.model_dump()
            
            # Send HTTP request
            async with self.session.post(
                f"{target_url}/mcp/message",
                json=message_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    self.logger.debug(f"Message sent successfully to {target_agent}")
                    return True
                else:
                    self.logger.error(f"Failed to send message: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
            
    async def send_request(self, recipient: str, method: str, params: Dict[str, Any] = None, timeout: int = 30) -> ResponseMessage:
        """Send a request and wait for response"""
        request = RequestMessage(
            sender=self.agent_name,
            recipient=recipient,
            method=method,
            params=params or {},
            content={"method": method, "params": params or {}},
            timeout_seconds=timeout
        )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request.id] = future
        
        try:
            # Send request
            success = await self.send_message(request, recipient)
            if not success:
                raise Exception("Failed to send request")
                
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request.id, None)
            raise Exception(f"Request timeout after {timeout} seconds")
        except Exception as e:
            self.pending_requests.pop(request.id, None)
            raise e
            
    async def broadcast_notification(self, event: str, data: Dict[str, Any] = None, recipients: List[str] = None):
        """Broadcast a notification to multiple agents"""
        notification = create_notification(self.agent_name, event, data)
        
        if recipients:
            # Send to specific recipients
            for recipient in recipients:
                notification.recipient = recipient
                await self.send_message(notification, recipient)
        else:
            # Broadcast to all known agents (implementation depends on discovery service)
            self.logger.info(f"Broadcasting notification: {event}")
            
    def _get_agent_endpoint(self, agent_name: str) -> str:
        """Get the endpoint URL for an agent (simplified implementation)"""
        # In a real implementation, this would use a discovery service
        # For now, assume all agents are on the same host with different ports
        return f"http://{self.host}:{self.port + hash(agent_name) % 1000}"