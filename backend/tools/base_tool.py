# Base class for all tools
# We can define common methods or properties here later

class BaseTool:
    name: str = "Base Tool"
    description: str = "Base class for tools."

    def run(self, *args, **kwargs):
        raise NotImplementedError("This method should be implemented by subclasses.") 