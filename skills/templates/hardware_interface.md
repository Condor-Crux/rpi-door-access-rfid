# Hardware Controller Mock Template

This template is for the AI agent when generating hardware abstractions.

```python
from abc import ABC, abstractmethod

class BaseController(ABC):
    @abstractmethod
    def read_state(self) -> dict:
        pass

    @abstractmethod
    def toggle(self, state: bool) -> None:
        pass
```
