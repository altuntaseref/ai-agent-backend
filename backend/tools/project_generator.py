import os
import json
import requests
from pydantic import BaseModel, Field # FilePath kaldırıldı çünkü string olarak alacağız
from typing import Type, Optional

from langchain.tools import BaseTool # Use Langchain's BaseTool for better integration

import config
import prompts

# --- Input Schema Definition using Pydantic --- 
class ProjectGeneratorInput(BaseModel):
    """Input schema for the ProjectGeneratorTool."""
    projectName: str = Field(description="The name of the project (e.g., test-service).")
    packageName: str = Field(description="The base package name for the generated code (e.g., com.example.myproject).")
    baseUrl: str = Field(description="The base URL of the target system (e.g., https://test.com).")
    username: str = Field(description="Username for accessing the target system.")
    password: str = Field(description="Password for accessing the target system.")
    apiKey: str = Field(description="API key, if required for the target system.")
    systemName: str = Field(description="The type or name of the target system (e.g., test).")
    sslCerIsRequired: bool = Field(description="Whether SSL certificate verification is required for the baseUrl.")
    gitlabRepoUrl: str = Field(description="The full URL of the GitLab repository (e.g., https://gitlab.com/rest-passthrough/test-service.git).")
    postman_file_path: str = Field(description="The local file path to the Postman collection JSON file. This should be the path provided by the system.")

# --- Tool Implementation --- 
class ProjectGeneratorTool(BaseTool):
    """Tool to generate a project by calling the Spring Boot service."""
    name: str = "project_generator"
    description: str = (
        "Generates a project structure based on a Postman collection and configuration details. "
        "Use this tool when the user uploads a Postman collection and wants to generate a project. "
        "Required parameters include: project name, package name, target system base URL, credentials, "
        "system name, SSL requirement, GitLab repository URL, and the path to the uploaded Postman collection file."
    )
    args_schema: Type[BaseModel] = ProjectGeneratorInput

    def _run(
        self, 
        projectName: str,
        packageName: str,
        baseUrl: str,
        username: str,
        password: str,
        apiKey: str,
        systemName: str,
        sslCerIsRequired: bool,
        gitlabRepoUrl: str,
        postman_file_path: str # Artık FilePath değil, düz string olarak alınıyor
    ) -> str:
        """Executes the project generation API call."""
        print(f"ProjectGeneratorTool: Starting project generation with parameters:")
        print(f"  projectName: {projectName}")
        print(f"  packageName: {packageName}")
        print(f"  baseUrl: {baseUrl}")
        print(f"  username: {username}")
        print(f"  systemName: {systemName}")
        print(f"  sslCerIsRequired: {sslCerIsRequired}")
        print(f"  gitlabRepoUrl: {gitlabRepoUrl}")
        print(f"  postman_file_path: {postman_file_path}")
        
        # Dosyanın var olup olmadığını kontrol et
        if not os.path.exists(postman_file_path):
            print(f"ERROR: Postman file not found at: {postman_file_path}")
            return prompts.FILE_NOT_FOUND_PROMPT.format(file_path=postman_file_path)
            
        # Dosyanın bir Postman koleksiyonu olduğunu doğrula
        try:
            with open(postman_file_path, 'r', encoding='utf-8') as f:
                json_content = json.load(f)
                
            # Çok basit bir Postman doğrulaması (main.py'deki daha ayrıntılı versiyonudur)
            if not isinstance(json_content, dict) or not any(key in json_content for key in ["info", "item"]):
                print(f"ERROR: File at {postman_file_path} is not a valid Postman collection")
                return "Belirtilen dosya geçerli bir Postman koleksiyonu değil. Lütfen formatı kontrol edin."
        except json.JSONDecodeError:
            print(f"ERROR: File at {postman_file_path} is not a valid JSON file")
            return "Belirtilen dosya geçerli bir JSON dosyası değil. Lütfen formatı kontrol edin."
        except Exception as e:
            print(f"ERROR validating Postman collection: {e}")
            return f"Postman koleksiyonu doğrulanırken bir hata oluştu: {e}"

        # Construct the request JSON string from arguments
        request_data = {
            "projectName": projectName,
            "packageName": packageName,
            "baseUrl": baseUrl,
            "username": username,
            "password": password,
            "apiKey": apiKey,
            "systemName": systemName,
            "sslCerIsRequired": sslCerIsRequired,
            "gitlabRepoUrl": gitlabRepoUrl
        }
        request_json_str = json.dumps(request_data)

        # Get API endpoint from config
        api_endpoint = config.PROJECT_GENERATOR_API_URL 
        if not api_endpoint:
            print("ERROR: PROJECT_GENERATOR_API_URL environment variable not set")
            return "Hata: PROJECT_GENERATOR_API_URL çevre değişkeni ayarlanmamış. Lütfen .env dosyasını kontrol edin."

        try:
            # Prepare files for multipart/form-data request
            with open(postman_file_path, 'rb') as postman_file:
                files = {
                    'request': (None, request_json_str, 'application/json'), # String part
                    'postmanFile': (os.path.basename(postman_file_path), postman_file, 'application/json') # File part
                }

                # Make the POST request
                print(f"Calling project generator API at {api_endpoint}")
                print(f"Request content type: multipart/form-data with {len(request_json_str)} bytes of JSON and Postman file")
                response = requests.post(
                    api_endpoint, 
                    files=files, 
                    verify=sslCerIsRequired,
                    timeout=120  # 2 dakika timeout ekleyelim, çünkü proje oluşturma uzun sürebilir
                )

                # Response status and headers for debug
                print(f"API Response status: {response.status_code}")
                print(f"API Response headers: {response.headers}")

                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()

                # Başarılı yanıt
                try:
                    json_response = response.json()
                    print(f"API Response success: {json_response}")
                    
                    # İş tamamlandıktan sonra dosyayı kaldırmayı deneyelim
                    try:
                        # Dikkat: Eğer bu noktada dosya hala kullanılıyorsa hata verebilir
                        os.remove(postman_file_path)
                        print(f"Temporary Postman collection file removed: {postman_file_path}")
                    except OSError as e:
                        print(f"Could not remove temporary file: {postman_file_path}, Error: {e}")
                        
                    return f"""Proje başarıyla oluşturuldu!
                    
Proje Adı: {projectName}
Paket Adı: {packageName}
GitLab URL: {gitlabRepoUrl}

API yanıtı: {json.dumps(json_response, indent=2, ensure_ascii=False)}

Projenizi GitLab'dan çekip kullanmaya başlayabilirsiniz.
"""
                except json.JSONDecodeError:
                    print(f"API Response is not valid JSON: {response.text[:200]}...")  # İlk 200 karakteri göster
                    return f"API çağrısı başarılı, ancak yanıt geçerli bir JSON formatında değil: {response.text[:500]}"

        except FileNotFoundError:
            print(f"ERROR: File not found during API call: {postman_file_path}")
            # Use the prompt for file not found
            return prompts.FILE_NOT_FOUND_PROMPT.format(file_path=postman_file_path)
        except requests.exceptions.RequestException as e:
            # Use the prompt for API errors
            error_message = f"{type(e).__name__}: {e}" # Get exception type and message
            print(f"ERROR: API request failed: {error_message}")
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" - Yanıt: {e.response.text[:500]}"  # Sınırlandır, çok uzun olabilir
            return prompts.API_ERROR_PROMPT.format(error_message=error_message)
        except Exception as e:
            # Catch any other unexpected errors
            print(f"ERROR: Unexpected error during project generation: {e}")
            return f"Beklenmeyen bir hata oluştu: {e}"

    # Note: _arun can be implemented for asynchronous execution if needed later 