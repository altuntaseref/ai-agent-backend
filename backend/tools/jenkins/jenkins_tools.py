import os
import json
import requests
from pydantic import BaseModel, Field
from typing import Type, Optional

from langchain.tools import BaseTool

import config
import prompts

# --- Input Schema Definitions using Pydantic --- 

class CreatePipelineInput(BaseModel):
    """Input schema for the CreatePipelineTool."""
    jobName: str = Field(description="The name of the Jenkins job/pipeline to create (e.g., product-passthrough-service).")

class TriggerPipelineInput(BaseModel):
    """Input schema for the TriggerPipelineTool."""
    jobName: str = Field(description="The name of the Jenkins job/pipeline to trigger (e.g., product-passthrough-service).")

class PipelineStatusInput(BaseModel):
    """Input schema for the PipelineStatusTool."""
    jobName: str = Field(description="The name of the Jenkins job/pipeline to check status (e.g., product-passthrough-service).")

class AppHealthCheckInput(BaseModel):
    """Input schema for the AppHealthCheckTool."""
    appName: str = Field(description="The name of the application to check health status (e.g., customer-service).")

# --- Tool Implementations --- 

class CreatePipelineTool(BaseTool):
    """Tool to create a Jenkins pipeline."""
    name: str = "create_pipeline"
    description: str = (
        "Creates a new Jenkins pipeline for a project. "
        "Use this tool when the user wants to set up a CI/CD pipeline for their project. "
        "This is typically done after a project has been generated. "
        "Required parameter: jobName (the name of the Jenkins job, usually same as the project name)."
    )
    args_schema: Type[BaseModel] = CreatePipelineInput

    def _run(self, jobName: str) -> str:
        """Creates a new Jenkins pipeline for the specified job name."""
        print(f"CreatePipelineTool: Creating pipeline for job: {jobName}")
        
        # Construct the request payload
        request_data = {
            "jobName": jobName
        }
        
        # Get API endpoint
        base_url = config.JENKINS_API_BASE_URL
        if not base_url:
            print("ERROR: JENKINS_API_BASE_URL environment variable not set")
            return "Hata: JENKINS_API_BASE_URL çevre değişkeni ayarlanmamış. Lütfen .env dosyasını kontrol edin."
        
        api_endpoint = f"{base_url}/api/v1/jenkins/create/pipeline"
        
        try:
            # Make the POST request
            print(f"Calling Jenkins Create Pipeline API at: {api_endpoint}")
            print(f"Request payload: {request_data}")
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                api_endpoint,
                json=request_data,
                headers=headers,
                timeout=60  # 1 dakika timeout
            )
            
            # Log response details
            print(f"API Response status: {response.status_code}")
            print(f"API Response headers: {response.headers}")
            
            # Raise exception for bad status codes
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                json_response = response.json()
                print(f"API Response success: {json_response}")
                return f"""Pipeline başarıyla oluşturuldu!

Job Adı: {jobName}

Pipeline artık Jenkins'te kuruldu. Şimdi pipeline'ı tetiklemek ister misiniz?
"""
            except json.JSONDecodeError:
                # If response is not JSON, return text
                return f"Pipeline oluşturma başarılı, ancak yanıt JSON formatında değil: {response.text[:500]}"
                
        except requests.exceptions.RequestException as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"ERROR: Jenkins API request failed: {error_message}")
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" - Yanıt: {e.response.text[:500]}"
            return prompts.API_ERROR_PROMPT.format(error_message=error_message)
        except Exception as e:
            print(f"ERROR: Unexpected error during pipeline creation: {e}")
            return f"Pipeline oluşturma sırasında beklenmeyen bir hata oluştu: {e}"

class TriggerPipelineTool(BaseTool):
    """Tool to trigger a Jenkins pipeline."""
    name: str = "trigger_pipeline"
    description: str = (
        "Triggers an existing Jenkins pipeline to run. "
        "Use this tool when the user wants to start a build for their project. "
        "This is typically done after a pipeline has been created. "
        "Required parameter: jobName (the name of the Jenkins job to trigger)."
    )
    args_schema: Type[BaseModel] = TriggerPipelineInput

    def _run(self, jobName: str) -> str:
        """Triggers the Jenkins pipeline for the specified job name."""
        print(f"TriggerPipelineTool: Triggering pipeline for job: {jobName}")
        
        # Get API endpoint
        base_url = config.JENKINS_API_BASE_URL
        if not base_url:
            print("ERROR: JENKINS_API_BASE_URL environment variable not set")
            return "Hata: JENKINS_API_BASE_URL çevre değişkeni ayarlanmamış. Lütfen .env dosyasını kontrol edin."
        
        api_endpoint = f"{base_url}/api/v1/jenkins/trigger/{jobName}"
        
        try:
            # Make the POST request
            print(f"Calling Jenkins Trigger Pipeline API at: {api_endpoint}")
            
            response = requests.post(
                api_endpoint,
                timeout=60  # 1 dakika timeout
            )
            
            # Log response details
            print(f"API Response status: {response.status_code}")
            print(f"API Response headers: {response.headers}")
            
            # Raise exception for bad status codes
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                json_response = response.json()
                print(f"API Response success: {json_response}")
                return f"""Pipeline başarıyla tetiklendi!

Job Adı: {jobName}

Build işlemi başlatıldı. Build durumunu kontrol etmek için pipeline durumunu sorgulayabilirsiniz.
"""
            except json.JSONDecodeError:
                # If response is not JSON, return text
                return f"Pipeline tetikleme başarılı, ancak yanıt JSON formatında değil: {response.text[:500]}"
                
        except requests.exceptions.RequestException as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"ERROR: Jenkins API request failed: {error_message}")
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" - Yanıt: {e.response.text[:500]}"
            return prompts.API_ERROR_PROMPT.format(error_message=error_message)
        except Exception as e:
            print(f"ERROR: Unexpected error during pipeline triggering: {e}")
            return f"Pipeline tetikleme sırasında beklenmeyen bir hata oluştu: {e}"

class PipelineStatusTool(BaseTool):
    """Tool to check the status of a Jenkins pipeline."""
    name: str = "pipeline_status"
    description: str = (
        "Checks the status of an existing Jenkins pipeline. "
        "Use this tool when the user wants to know the current state of their build. "
        "Required parameter: jobName (the name of the Jenkins job to check)."
    )
    args_schema: Type[BaseModel] = PipelineStatusInput

    def _run(self, jobName: str) -> str:
        """Checks the status of the Jenkins pipeline for the specified job name."""
        print(f"PipelineStatusTool: Checking status for job: {jobName}")
        
        # Get API endpoint
        base_url = config.JENKINS_API_BASE_URL
        if not base_url:
            print("ERROR: JENKINS_API_BASE_URL environment variable not set")
            return "Hata: JENKINS_API_BASE_URL çevre değişkeni ayarlanmamış. Lütfen .env dosyasını kontrol edin."
        
        api_endpoint = f"{base_url}/api/v1/jenkins/status/{jobName}"
        
        try:
            # Make the GET request
            print(f"Calling Jenkins Status API at: {api_endpoint}")
            
            response = requests.get(
                api_endpoint,
                timeout=30  # 30 saniye timeout
            )
            
            # Log response details
            print(f"API Response status: {response.status_code}")
            print(f"API Response headers: {response.headers}")
            
            # Raise exception for bad status codes
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                json_response = response.json()
                print(f"API Response success: {json_response}")
                
                # Translate status to Turkish (if needed)
                status = json_response.get("status", "UNKNOWN")
                status_tr = {
                    "SUCCESS": "BAŞARILI",
                    "FAILURE": "BAŞARISIZ",
                    "UNSTABLE": "KARARLI DEĞİL",
                    "IN_PROGRESS": "DEVAM EDİYOR",
                    "ABORTED": "İPTAL EDİLDİ",
                    "NOT_BUILT": "HENÜZ ÇALIŞTIRILMADI",
                    "UNKNOWN": "BİLİNMİYOR"
                }.get(status, status)
                
                return f"""Pipeline Durumu:

Job Adı: {jobName}
Durum: {status_tr}

Detaylar: {json.dumps(json_response, indent=2, ensure_ascii=False)}

Bu pipeline'ı tetiklemek veya başka işlemler yapmak ister misiniz?
"""
            except json.JSONDecodeError:
                # If response is not JSON, return text
                return f"Pipeline durum sorgusu başarılı, ancak yanıt JSON formatında değil: {response.text[:500]}"
                
        except requests.exceptions.RequestException as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"ERROR: Jenkins API request failed: {error_message}")
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" - Yanıt: {e.response.text[:500]}"
            return prompts.API_ERROR_PROMPT.format(error_message=error_message)
        except Exception as e:
            print(f"ERROR: Unexpected error during pipeline status check: {e}")
            return f"Pipeline durumu sorgulanırken beklenmeyen bir hata oluştu: {e}"

class AppHealthCheckTool(BaseTool):
    """Tool to check the health status of an application and return application url."""
    name: str = "app_health_check"
    description: str = (
        "Checks the health status of a deployed application. "
        "Use this tool when the user wants to verify if a service is running and healthy. "
        "Required parameter: appName (the name of the application to check, e.g., customer-service)."
    )
    args_schema: Type[BaseModel] = AppHealthCheckInput

    def _run(self, appName: str) -> str:
        """Checks the health status of the specified application."""
        print(f"AppHealthCheckTool: Checking health for application: {appName}")
        
        # Get API endpoint
        base_url = config.JENKINS_API_BASE_URL
        if not base_url:
            print("ERROR: JENKINS_API_BASE_URL environment variable not set")
            return "Hata: API temel URL'si ayarlanmamış. Lütfen .env dosyasını kontrol edin."
        
        api_endpoint = f"{base_url}/api/v1/app-health/check/{appName}"
        
        try:
            # Make the GET request
            print(f"Calling App Health Check API at: {api_endpoint}")
            
            response = requests.get(
                api_endpoint,
                timeout=30  # 30 saniye timeout
            )
            
            # Log response details
            print(f"API Response status: {response.status_code}")
            print(f"API Response headers: {response.headers}")
            
            # Raise exception for bad status codes
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                json_response = response.json()
                print(f"API Response success: {json_response}")
                
                # Extract health status from the response
                status = json_response.get("status", "UNKNOWN")
                details = json_response.get("details", {})
                is_healthy = (status == "UP")
                details = json_response.get("details", {})
                url = details.get("URL", None)
                
                # Translate status to user-friendly Turkish
                health_status_tr = "Uygulama sağlıklı şekiled çalışıyor" if is_healthy else "Uygulama çalışmıyor"
                
                return f"""Uygulama Sağlık Durumu:

Uygulama Adı: {appName}
Durum: {health_status_tr}
URL: {url}

Detaylar: {json.dumps(details, indent=2, ensure_ascii=False)}

Bu uygulamanın pipeline'ını tetiklemek veya başka bir uygulama kontrolü yapmak ister misiniz?
"""
            except json.JSONDecodeError:
                # Response may not be JSON, try to interpret raw response
                if response.status_code == 200:
                    return f"{appName} uygulaması çalışıyor ve sağlıklı görünüyor."
                else:
                    return f"Uygulama sağlık kontrolü yanıtı beklenmeyen formatta: {response.text[:500]}"
                
        except requests.exceptions.ConnectionError:
            return f"Bağlantı hatası: {appName} uygulamasına erişilemiyor. Uygulama kapalı veya yanıt vermiyor olabilir."
        except requests.exceptions.Timeout:
            return f"Zaman aşımı: {appName} uygulaması yanıt verme süresini aştı."
        except requests.exceptions.RequestException as e:
            error_message = f"{type(e).__name__}: {e}"
            print(f"ERROR: Health check API request failed: {error_message}")
            if hasattr(e, 'response') and e.response is not None:
                error_message += f" - Yanıt: {e.response.text[:500]}"
            return prompts.API_ERROR_PROMPT.format(error_message=error_message)
        except Exception as e:
            print(f"ERROR: Unexpected error during health check: {e}")
            return f"Uygulama sağlık kontrolü sırasında beklenmeyen bir hata oluştu: {e}" 