"""Wait System Member Module.

This module provides the Wait member, a system utility for pausing or delaying
workflow execution for a specified duration. Wait steps enable workflows to
introduce time-based delays, synchronize with external events, or throttle
processing.

Key Features:
- Pause workflow execution for a configurable duration
- Support for seconds, minutes, or custom time units
- Useful for rate-limiting, polling, or timed actions
- Can be used to synchronize with external systems or events

Wait steps allow workflows to control timing, pacing, and synchronization,
enabling more flexible and robust automation.

"""

from typing import Dict, Any, Union

from plugins.workflows.members import Member
from utils.helpers import set_module_type
import asyncio


@set_module_type(module_type='Members', settings='wait_settings')
class Wait(Member):
    default_avatar = ':/resources/icon-wait.png'
    default_name = 'Wait'
    workflow_insert_mode = 'single'
    OUTPUT = None

    @property
    def INPUTS(self):
        return {
            'CONFIG': {
                'duration': float,  # seconds
                'unit': str,        # 'seconds', 'minutes', etc. (optional)
            },
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def run(self):
        duration = self.config.get('duration', 1)
        unit = self.config.get('unit', 'seconds')
        # Convert to seconds if needed
        if unit == 'minutes':
            duration = duration * 60
        elif unit == 'hours':
            duration = duration * 3600
        # else assume seconds
        print(f'Waiting for {duration} {unit}')
        await asyncio.sleep(duration)
        print(f'Waited for {duration} {unit}')
        self.workflow.save_message('sys', f'Waited for {duration} {unit}', self.full_member_id())
        yield 'SYS', 'SKIP'

    # async def run(self):
