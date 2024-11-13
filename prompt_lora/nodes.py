from torch import Tensor
import comfy.sd
import comfy.model_patcher
import comfy.utils
import folder_paths
import logging
from typing import Any, Dict, TypedDict, List
import re

logging.basicConfig()
log = logging.getLogger("comfyui-prompt-lora")

class CachedLora(TypedDict):
    name: str
    filepath: str
    lora: (Dict[str, Tensor] | Any)

class LoraParams(TypedDict):
    name: str
    weight: float
    weight_clip: float
    text: str

# Function to parse LoRA details from the prompt
def parse_lora_details(prompt) -> List[LoraParams]:
    try:

        pattern = r"<([^>]+)>"
        ret: List[LoraParams] = []
        matches: List[str] = re.findall(pattern, prompt)
        for m in matches:
            if m.startswith('lora'):
                spl = m.split(':')
                if len(spl) > 2:
                    name = spl[1].strip()
                    try:
                        weight_str = spl[2].strip()
                        weight = float(weight_str)
                        weight_clip = 1
                        try:
                            weight_clip = float(spl(3).strip())
                        except:
                            log.debug(f'no clip weight found for {name}')
                            pass
                        ret.append({ "name": name, "weight": weight, 'weight_clip': weight_clip, "text": f'<{m}>' })
                        
                    except ValueError:
                        log.error(f'invalid weight for {name}')
                        
        return ret
    except Exception as e:
        print(f"Error parsing prompt: {e}")
        return []


# CLIPTextEncode.encode
def prompt_encode(clip: comfy.sd.CLIP, text: str):
    tokens = clip.tokenize(text)
    output = clip.encode_from_tokens(tokens, return_pooled=True, return_dict=True)
    cond = output.pop("cond")
    return ([[cond, output]], )

class PromptLora:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "positive": ("STRING", {"multiline": True}),
                "negative": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("model", "clip", "positive", "negative")
    FUNCTION = "apply"
    CATEGORY = 'idk yet'

    cache = dict()

    def apply(self, model: comfy.model_patcher.ModelPatcher, clip: comfy.sd.CLIP, positive: str, negative: str):

        # TODO, allow to pass just lora name, not the full path, will need to cache all names and their associated paths

        loras: list[LoraParams] = parse_lora_details(positive)

        model_lora = model
        clip_lora = clip

        used_lora_names: List[str] = []

        for lora_detail in loras:
            lora_weight = lora_detail.get("weight")
            lora_clip_weight = lora_detail.get("weight_clip")
            lora_name = lora_detail.get("name")

            used_lora_names.append(lora_name)

            if lora_name in self.cache:
                cached: CachedLora = self.cache.get(lora_name)
                lora = cached.get('lora')
            else:
                lora_path = folder_paths.get_full_path("loras", lora_name)
                lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                self.cache[lora_name] = CachedLora(name=lora_name, lora=lora, filepath=lora_path)

            # remove the lora text from the positive prompt
            positive = positive.replace(lora_detail.get('text'), '')

            model_lora, clip_lora = comfy.sd.load_lora_for_models(
                model_lora, clip_lora, lora, lora_weight, lora_clip_weight
            )

        # TODO, remove lora from cache if its not in used_lora_names

        p = prompt_encode(clip_lora, positive)[0]
        n = prompt_encode(clip_lora, negative)[0]

        return (model_lora, clip_lora, p, n)