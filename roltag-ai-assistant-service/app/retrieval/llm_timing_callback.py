import time

from langchain_core.callbacks import BaseCallbackHandler


class LlmTimingCallback(BaseCallbackHandler):
    """Callback handler that logs the time taken for LLM calls."""

    def on_llm_start(self, seialized, messages, **kwargs):
        self.start_time = time.perf_counter()

    def on_llm_end(self, response, **kwargs):
       self.elapsed_ms = round((time.perf_counter() - self.start_time) * 1000, 1)