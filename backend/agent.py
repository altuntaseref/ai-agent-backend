# from langchain_openai import ChatOpenAI # OpenAI kullanmayacağımız için kaldırıldı
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import re
import os

import config
from tools.base_tool import BaseTool
import prompts # Import the prompts module

# TODO: Dynamically load tools from the tools directory

class SoftwareDevAgent:
    def __init__(self, tools: list[BaseTool]):
        self.llm = self._initialize_llm()
        self.tools = tools
        if not self.tools:
             print("Warning: Agent initialized with no tools.")
             # Optionally raise an error or handle appropriately
             # raise ValueError("Agent must be initialized with at least one tool.")

        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        # --- Format Tools for Prompt --- 
        # Create a formatted string describing the tools for the system prompt
        # LangChain's BaseTool has .name and .description attributes
        formatted_tools = "\n".join([f"> {tool.name}: {tool.description}" for tool in self.tools])
        tool_names = ", ".join([tool.name for tool in self.tools])
        
        # Format the system prompt with the actual tool details
        system_prompt_formatted = prompts.AGENT_SYSTEM_PROMPT.format(
            tools=formatted_tools,
            tool_names=tool_names
        )

        # --- Create Prompt Template --- 
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_formatted), # Use the formatted prompt
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # --- Create Agent --- 
        # Ensure the tools passed here are compatible with the agent type
        # For create_tool_calling_agent, the tools should ideally be BaseTool instances
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)

        # --- Create Agent Executor --- 
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
        )

    def _initialize_llm(self):
        """Initializes the Google Gemini language model."""
        if config.LLM_PROVIDER == "gemini":
            if not config.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            # Postman koleksiyonlarını daha iyi işleyebilmesi için temayı biraz yükselttik
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash-latest", 
                google_api_key=config.GOOGLE_API_KEY, 
                temperature=0.3,
                convert_system_message_to_human=True
            )
        else:
            raise ValueError(f"Unsupported LLM provider configured: {config.LLM_PROVIDER}")

    # _load_tools is not used if tools are passed during initialization
    # def _load_tools(self):
    #     """Loads tools dynamically from the tools directory (placeholder)."""
    #     # TODO: Implement dynamic tool loading later
    #     print("Placeholder: Tool loading not yet implemented.")
    #     return []

    def extract_project_details(self, user_input):
        """Kullanıcı girdisinden proje detaylarını çıkarmaya çalışır."""
        details = {}
        
        # Yaygın proje parametreleri için regex kalıpları
        patterns = {
            "projectName": r"[Pp]roje\s+ad[ıi][\s:]+([a-zA-Z0-9-_]+)",
            "packageName": r"[Pp]aket\s+ad[ıi][\s:]+([a-zA-Z0-9._]+)",
            "baseUrl": r"[Bb]ase[Uu][Rr][Ll][\s:]+([a-zA-Z0-9:/_.-]+)",
            "username": r"[Kk]ullan[ıi]c[ıi]\s+ad[ıi][\s:]+([a-zA-Z0-9_-]+)",
            "systemName": r"[Ss]istem\s+ad[ıi][\s:]+([a-zA-Z0-9_-]+)",
            "gitlabRepoUrl": r"[Gg]it[Ll]ab[\s:]+([a-zA-Z0-9:/_.-]+\.git)",
        }
        
        # Kalıpları kullanarak değerleri çıkar
        for key, pattern in patterns.items():
            match = re.search(pattern, user_input)
            if match:
                details[key] = match.group(1)
                
        # Boolean değeri için özel işlem
        ssl_match = re.search(r"[Ss][Ss][Ll][\s:]+([Tt]rue|[Ff]alse|[Ee]vet|[Hh]ay[ıi]r)", user_input)
        if ssl_match:
            value = ssl_match.group(1).lower()
            details["sslCerIsRequired"] = value in ["true", "evet"]
                
        return details

    def run(self, user_input: str):
        """Agent'ı verilen kullanıcı girdisiyle çalıştırır ve Türkçe yanıt verir."""
        try:
            # Postman koleksiyonu dosya yolunu mesajdan algılamaya çalış
            postman_path = None
            file_path_indicator = "System Note: User uploaded a Postman collection"
            
            # Kullanıcı bir Postman koleksiyonu yüklediyse bunu algıla
            if file_path_indicator in user_input:
                # "It is available at the temporary path: PATH" ifadesini bul
                path_match = re.search(r"temporary path: ([^\]]+)", user_input)
                if path_match:
                    postman_path = path_match.group(1).strip()
                    print(f"Detected Postman collection path: {postman_path}")
            
            # Ek bilgi ekleyerek Agent'in görevi daha iyi anlamasını sağla
            if postman_path:
                # Dosyanın gerçekten var olup olmadığını kontrol et
                if os.path.exists(postman_path):
                    # Kullanıcı girdisinden proje detaylarını çıkarmaya çalış
                    project_details = self.extract_project_details(user_input)
                    
                    # Çıkarılan detayların sayısına bağlı olarak özel bir mesaj oluştur
                    if len(project_details) >= 4:  # Birçok parametre sağlanmışsa
                        tool_reminder = prompts.TOOL_USAGE_REMINDER
                    else:
                        tool_reminder = ""
                    
                    enhanced_input = f"""
{user_input}

[System Guidance: The user has uploaded a Postman collection file available at: {postman_path}]
[System Guidance: This is a project generation request. You MUST use the project_generator tool once you have all required parameters.]
{tool_reminder}
"""
                else:
                    enhanced_input = f"""
{user_input}

[System Warning: The user uploaded a Postman collection, but the file at path {postman_path} no longer exists or is not accessible. Please inform the user that they may need to upload the file again.]
"""
            else:
                enhanced_input = user_input
            
            # AgentExecutor'ı çalıştır
            response = self.agent_executor.invoke({"input": enhanced_input})
            english_output = response.get("output", "Üzgünüm, bir yanıt oluşturamadım.") 
            
            # TODO: Yanıtı doğrudan Türkçe almak için ileride daha iyi bir yöntem eklenmeli
            return english_output

        except Exception as e:
            print(f"Agent çalıştırması başarısız oldu: {e}")
            # Hata mesajlarını da Türkçeleştirebiliriz
            if "FileNotFoundError" in str(e):
                 return prompts.FILE_NOT_FOUND_PROMPT.format(file_path="belirtilen dosya") # Daha iyi hata ayrıştırma gerekir
            elif "RequestException" in str(e):
                 return prompts.API_ERROR_PROMPT.format(error_message=str(e))
            else:
                 return f"Bir hata oluştu: {e}"

# Example Usage (for testing later)
if __name__ == "__main__":
    print("This script is not intended to be run directly anymore.")
    print("Please run main.py from the backend directory.")
    # Example of direct run (requires manual tool instantiation):
    # from tools.project_generator import ProjectGeneratorTool
    # try:
    #     tool1 = ProjectGeneratorTool()
    #     agent = SoftwareDevAgent(tools=[tool1])
    #     # ... rest of the test loop ...
    # except Exception as e:
    #     print(f"Error during direct test: {e}") 