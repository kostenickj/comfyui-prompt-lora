import os
import sys
import logging

from .prompt_lora.nodes import PromptLora

log = logging.getLogger("comfyui-prompt-lora")
log.propagate = False
if not log.handlers:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("[%(levelname)s] PromptLora: %(message)s"))
    log.addHandler(h)

if os.environ.get("COMFY_DEBUG"):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))


NODE_CLASS_MAPPINGS = {
    "PromptLora": PromptLora
}
NODE_DISPLAY_NAME_MAPPINGS = {
  'PromptLora': 'Prompt Lora',
}