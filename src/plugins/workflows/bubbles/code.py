"""Code Message Role GUI Module.

This module provides the CodeBubble class, a specialized message role
for displaying and executing code content in the chat interface. Code roles
enable syntax highlighting, code execution, and interactive code manipulation
within conversations.

Key Features:
- Code syntax highlighting and formatting
- Interactive code execution and rerun capabilities
- Integration with code execution environments
- Support for multiple programming languages
- Code editing and modification
- Output display and error handling
- Integration with Open Interpreter
- Automatic code execution timing

Code roles provide a powerful interface for viewing, editing, and
executing code within conversations, enabling interactive programming
and code collaboration with AI systems.
"""  # unchecked

from plugins.workflows.bubbles import MessageButton, MessageBubble
from utils.helpers import message_button


class CodeBubble(MessageBubble):
    def __init__(self, parent, message):
        super().__init__(
            parent=parent,
            message=message,
            readonly=False,
            autorun_button='btn_rerun',
            autorun_secs=5,
        )

    @message_button('btn_rerun')
    class RerunButton(MessageButton):
        def __init__(self, parent):
            super().__init__(parent=parent,
                             icon_path=':/resources/icon-run-solid.png')

        def on_clicked(self):
            from utils.helpers import split_lang_and_code
            if self.msg_container.parent.workflow.responding:
                return
            # self.msg_container.btn_countdown.hide()

            bubble = self.msg_container.bubble
            member_id = self.msg_container.member_id
            lang, code = split_lang_and_code(bubble.text)
            code = bubble.toPlainText()

            self.msg_container.check_to_start_a_branch(
                role=bubble.role,
                new_message=f'```{lang}\n{code}\n```',
                member_id=member_id
            )

            from plugins.openinterpreter.src import interpreter
            oi_res = interpreter.computer.run(lang, code)
            output = next(r for r in oi_res if r['format'] == 'output').get('content', '')
            self.msg_container.parent.send_message(
                output,
                role='output',
                as_member_id=member_id,
                feed_back=True,
                clear_input=False
            )
