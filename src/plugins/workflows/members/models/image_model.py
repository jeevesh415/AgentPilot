"""Image Model Member Module.

This module provides the ImageModel member, a specialized model for processing
and generating images within workflows. Image models enable AI-powered image
analysis, generation, and manipulation capabilities integrated with the
Agent Pilot ecosystem.

Key Features:
- AI-powered image generation and processing
- Integration with image generation APIs and models
- Text-to-image generation capabilities
- Image analysis and understanding
- Workflow integration for visual content creation
- Configurable image generation parameters
- Support for various image AI model providers
- Output handling for generated images

Image models expand workflow capabilities to include visual content
generation, analysis, and processing, enabling multimedia AI applications
within the Agent Pilot framework.
"""

from typing import Any

from plugins.workflows.members import Model
from utils.helpers import set_module_type


@set_module_type(module_type='Members', plugin='MODEL', settings='image_model_settings')
class ImageModel(Model):
    default_role = 'image'
    default_avatar = ':/resources/icon-image.png'
    default_name = 'Image Model'
    workflow_insert_mode = 'single'
    OUTPUT = 'IMAGE'

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'text': str,
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def receive(self):
        """The entry response method for the member."""
        yield self.default_role, 'TODO'
