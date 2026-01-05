import json
import base64
from pathlib import Path


def _get_cors_headers():
    """Get CORS headers for API responses."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Session-Id,X-Language,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS,PUT,DELETE",
        "Access-Control-Max-Age": "86400",
    }


def cors_handler(event, context):
    """Handle CORS preflight requests (OPTIONS)."""
    return {
        "statusCode": 200,
        "headers": _get_cors_headers(),
        "body": json.dumps({"message": "OK"}),
    }


def swagger_ui_handler(event, context):
    """Serve Swagger UI HTML."""
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return cors_handler(event, context)
    
    swagger_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Farmer RAG Voice API - Swagger UI</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui.min.css">
        <style>
            html { box-sizing: border-box; overflow: y scroll; }
            *, *:before, *:after { box-sizing: inherit; }
            body { margin: 0; padding: 0; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui.min.js"></script>
        <script>
            window.onload = function() {
                const ui = SwaggerUIBundle({
                    url: "./openapi.json",
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    requestInterceptor: (request) => {
                        // Add CORS-safe headers
                        request.headers['Content-Type'] = 'application/json';
                        return request;
                    }
                });
                window.ui = ui;
            };
        </script>
    </body>
    </html>
    """
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/html; charset=utf-8",
            **_get_cors_headers(),
        },
        "body": swagger_html,
    }


def openapi_spec_handler(event, context):
    """Serve OpenAPI specification."""
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return cors_handler(event, context)
    
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Farmer RAG Voice API",
            "description": "Voice-enabled RAG system for farmer queries with ASR, TTS, and text-based Q&A",
            "version": "1.0.0",
            "contact": {
                "name": "Farmer POC Team",
            }
        },
        "servers": [
            {
                "url": event.get("requestContext", {}).get("stage", "/Prod"),
                "description": "Current API Gateway"
            }
        ],
        "tags": [
            {
                "name": "RAG - Text Q&A",
                "description": "Text-based question answering with retrieval-augmented generation"
            },
            {
                "name": "Voice - Audio Upload",
                "description": "Manage audio file uploads to S3"
            },
            {
                "name": "Voice - Speech-to-Text (ASR)",
                "description": "Convert audio to text using speech recognition"
            },
            {
                "name": "Voice - Text-to-Speech (TTS)",
                "description": "Convert text to audio using text-to-speech synthesis"
            },
            {
                "name": "Health Check",
                "description": "API health monitoring"
            }
        ],
        "paths": {
            "/ask": {
                "get": {
                    "tags": ["RAG - Text Q&A"],
                    "summary": "Ask a question (GET method)",
                    "description": "Get an answer to a farmer-related question using RAG pipeline",
                    "parameters": [
                        {
                            "name": "query",
                            "in": "query",
                            "description": "The farmer question or query",
                            "required": True,
                            "schema": {
                                "type": "string",
                                "example": "What is the best time to plant rice?"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response with answer",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "question": {"type": "string", "example": "What is the best time to plant rice?"},
                                            "answer": {"type": "string", "example": "The best time to plant rice is during the monsoon season..."}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Missing query parameter",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "error": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "tags": ["RAG - Text Q&A"],
                    "summary": "Ask a question (POST method)",
                    "description": "Get an answer to a farmer-related question using RAG pipeline",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["question"],
                                    "properties": {
                                        "question": {
                                            "type": "string",
                                            "example": "How do I prevent crop diseases?"
                                        },
                                        "query": {
                                            "type": "string",
                                            "description": "Alternative to 'question' field",
                                            "example": "How do I prevent crop diseases?"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response with answer",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "question": {"type": "string"},
                                            "answer": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Missing question parameter"
                        }
                    }
                }
            },
            "/voice/upload-url": {
                "post": {
                    "tags": ["Voice - Audio Upload"],
                    "summary": "Get pre-signed S3 upload URL",
                    "description": "Generate a pre-signed URL for uploading audio files to S3",
                    "parameters": [
                        {
                            "name": "X-Language",
                            "in": "header",
                            "description": "Target language code (en, hi, od)",
                            "schema": {
                                "type": "string",
                                "enum": ["en", "hi", "od"],
                                "default": "en"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["filename", "content_type"],
                                    "properties": {
                                        "filename": {
                                            "type": "string",
                                            "example": "farmer_query.wav"
                                        },
                                        "content_type": {
                                            "type": "string",
                                            "example": "audio/wav",
                                            "enum": ["audio/wav", "audio/mpeg", "audio/mp3", "audio/ogg"]
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Pre-signed URL generated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "upload_url": {
                                                "type": "string",
                                                "description": "Pre-signed S3 upload URL"
                                            },
                                            "s3_key": {
                                                "type": "string",
                                                "description": "S3 object key for the uploaded file"
                                            },
                                            "expires_in": {
                                                "type": "integer",
                                                "description": "URL expiration time in seconds"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/voice/asr": {
                "post": {
                    "tags": ["Voice - Speech-to-Text (ASR)"],
                    "summary": "Convert audio to text",
                    "description": "Transcribe audio file to text using ASR (Automatic Speech Recognition)",
                    "parameters": [
                        {
                            "name": "X-Language",
                            "in": "header",
                            "description": "Audio language (en, hi, od)",
                            "schema": {
                                "type": "string",
                                "enum": ["en", "hi", "od"],
                                "default": "en"
                            }
                        },
                        {
                            "name": "X-Session-Id",
                            "in": "header",
                            "description": "Session ID for rate limiting",
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["s3_key"],
                                    "properties": {
                                        "s3_key": {
                                            "type": "string",
                                            "example": "audio/farmer_query_20240102_120000.wav",
                                            "description": "S3 key of the audio file to transcribe"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Transcription successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "transcription": {
                                                "type": "string",
                                                "example": "What is the best fertilizer for rice?"
                                            },
                                            "language": {
                                                "type": "string"
                                            },
                                            "confidence": {
                                                "type": "number",
                                                "description": "Confidence score (0-1)"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "429": {
                            "description": "Rate limit exceeded"
                        }
                    }
                }
            },
            "/voice/tts": {
                "post": {
                    "tags": ["Voice - Text-to-Speech (TTS)"],
                    "summary": "Convert text to audio",
                    "description": "Synthesize text to speech audio",
                    "parameters": [
                        {
                            "name": "X-Language",
                            "in": "header",
                            "description": "Output audio language (en, hi, od)",
                            "schema": {
                                "type": "string",
                                "enum": ["en", "hi", "od"],
                                "default": "en"
                            }
                        },
                        {
                            "name": "X-Session-Id",
                            "in": "header",
                            "description": "Session ID for rate limiting",
                            "schema": {
                                "type": "string"
                            }
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["text"],
                                    "properties": {
                                        "text": {
                                            "type": "string",
                                            "example": "The best time to plant rice is during the monsoon season.",
                                            "description": "Text to convert to speech"
                                        },
                                        "voice_id": {
                                            "type": "string",
                                            "example": "Joanna",
                                            "description": "Voice identifier (varies by language)"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Audio generated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "audio_url": {
                                                "type": "string",
                                                "description": "Pre-signed S3 URL for audio download"
                                            },
                                            "duration": {
                                                "type": "number",
                                                "description": "Audio duration in seconds"
                                            },
                                            "language": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "429": {
                            "description": "Rate limit exceeded"
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "tags": ["Health Check"],
                    "summary": "Health check endpoint",
                    "description": "Check API health status",
                    "responses": {
                        "200": {
                            "description": "API is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            **_get_cors_headers(),
        },
        "body": json.dumps(openapi_spec),
    }
