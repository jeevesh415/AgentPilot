from PySide6.QtWidgets import QDoubleSpinBox
# from PySide6.QtWidgets import QWidget
# from gui.util import CVBoxLayout


# class Float(QWidget):
#     option_schema = [
#         {
#             'text': 'Minimum',
#             'key': 'f_minimum',
#             'type': float,
#             'minimum': -3.402823466e+38,
#             'maximum': 3.402823466e+38,
#             'step': 0.1,
#             'default': 0.0,
#         },
#         {
#             'text': 'Maximum',
#             'key': 'f_maximum',
#             'type': float,
#             'minimum': -3.402823466e+38,
#             'maximum': 3.402823466e+38,
#             'step': 0.1,
#             'default': 1.0,
#         },
#         {
#             'text': 'Step',
#             'key': 'f_step',
#             'type': float,
#             'minimum': -3.402823466e+38,
#             'maximum': 3.402823466e+38,
#             'step': 0.1,
#             'default': 0.1,
#         }
#     ]

#     def __init__(self, parent, **kwargs):
#         super().__init__(parent)
#         minimum = kwargs.get('minimum', -3.402823466e+38)
#         maximum = kwargs.get('maximum', 3.402823466e+38)
#         style = kwargs.get('style', 'spinbox')  # spinbox / slider
#         step = kwargs.get('step', 0.1)
#         self.layout = CVBoxLayout(self)
#         self.inner_widget = None
#         if style == 'spinbox':
#             self.inner_widget = QDoubleSpinBox(parent)
#             self.inner_widget.setRange(minimum, maximum)
#             self.inner_widget.setSingleStep(step)
#         elif style == 'slider':
#             self.inner_widget = QSlider(parent)
#             # QSlider only works with integers, so we need to clamp the range
#             int_min = max(int(minimum), -2147483648)  # INT32_MIN
#             int_max = min(int(maximum), 2147483647)   # INT32_MAX
#             int_step = max(1, int(step))
#             self.inner_widget.setRange(int_min, int_max)
#             self.inner_widget.setSingleStep(int_step)
#         self.inner_widget.valueChanged.connect(parent.update_config)
#         self.layout.addWidget(self.inner_widget)

#     def get_value(self):
#         return self.inner_widget.value()
    
#     def set_value(self, value):
#         if not isinstance(value, float):  # todo clean
#             try:
#                 value = float(str(value))
#             except (ValueError, TypeError):
#                 raise ValueError(f"Invalid value: {value}")
#         self.inner_widget.setValue(value)  # not recursive, camelCase not snake_case
    
#     def clear_value(self):
#         self.inner_widget.setValue(0.0)

class Float(QDoubleSpinBox):
    option_schema = [
        {
            'text': 'Minimum',
            'key': 'f_minimum',
            'type': float,
            'minimum': -3.402823466e+38,
            'maximum': 3.402823466e+38,
            'step': 0.1,
            'default': 0.0,
        },
        {
            'text': 'Maximum',
            'key': 'f_maximum',
            'type': float,
            'minimum': -3.402823466e+38,
            'maximum': 3.402823466e+38,
            'step': 0.1,
            'default': 1.0,
        },
        {
            'text': 'Step',
            'key': 'f_step',
            'type': float,
            'minimum': -3.402823466e+38,
            'maximum': 3.402823466e+38,
            'step': 0.1,
            'default': 0.1,
        }
    ]

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        minimum = kwargs.get('minimum', -1.7976931348623157e+308)
        maximum = kwargs.get('maximum', 1.7976931348623157e+308)
        step = kwargs.get('step', 0.05)
        self.setRange(minimum, maximum)
        self.setSingleStep(step)
        self.valueChanged.connect(parent.update_config)

    def get_value(self):
        return self.value()

    def set_value(self, value):
        if not isinstance(value, float):
            try:
                value = float(str(value))
            except (ValueError, TypeError):
                value = 0.0
        self.setValue(value)  # not recursive, camelCase not snake_case

    def clear_value(self):
        self.setValue(0.0)