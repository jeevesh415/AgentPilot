import numpy as np
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QLabel
from gui.widgets.config_widget import ConfigWidget
from gui.util import CVBoxLayout, CHBoxLayout, IconButton, clear_layout, find_attribute
from utils.helpers import apply_alpha_to_hex, block_signals, display_message


class XAxisZoomViewBox:
    """
    Mixin for pyqtgraph.ViewBox that zooms only X axis unless mouse is over Y axis.

    Usage: class CustomViewBox(XAxisZoomViewBox, ViewBox): pass
    """

    def wheelEvent(self, ev, axis=None):
        plot_item = self.parentItem()
        if plot_item is not None:
            left_axis = plot_item.getAxis('left')
            if left_axis is not None:
                # Check if mouse is over the Y axis area
                if left_axis.geometry().contains(ev.scenePos()):
                    super().wheelEvent(ev, axis=1)
                    return
        super().wheelEvent(ev, axis=0)


class ChartWidget(ConfigWidget):
    """PyQtGraph candlestick chart widget for PriceFile data."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        try:
            import pyqtgraph as pg
            from pyqtgraph import PlotWidget, ViewBox
        except ImportError:
            display_message("PyQtGraph not installed. Please install it to use charting features:\n\npip install pyqtgraph")
            return

        CustomViewBox = type('CustomViewBox', (XAxisZoomViewBox, ViewBox), {})

        self.layout = CVBoxLayout(self)

        # Controls header
        controls_layout = CHBoxLayout()

        # Timeframe selector
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.setMinimumWidth(75)
        self.timeframe_combo.currentIndexChanged.connect(self.update_chart)
        controls_layout.addWidget(self.timeframe_combo)

        # Indicator button
        self.indicator_btn = IconButton(
            parent=self,
            icon_path=':/resources/icon-indicator.png',
            tooltip='Indicator',
            text='Indicators',
            size=24
        )
        self.indicator_btn.clicked.connect(self.build_indicator_plots)
        controls_layout.addWidget(self.indicator_btn)

        controls_layout.addStretch()

        # Refresh button
        self.refresh_btn = IconButton(
            parent=self,
            icon_path=':/resources/icon-refresh.png',
            tooltip='Refresh Chart Data',
            size=24
        )
        self.refresh_btn.clicked.connect(self.update_chart)
        controls_layout.addWidget(self.refresh_btn)

        self.layout.addLayout(controls_layout)

        # Main chart area with date axis
        date_axis = pg.DateAxisItem(orientation='bottom')
        self.chart_widget = PlotWidget(
            viewBox=CustomViewBox(),
            axisItems={'bottom': date_axis}
        )
        self.chart_widget.setStyleSheet("border: none;")
        vb = self.chart_widget.getPlotItem().getViewBox()
        vb.sigXRangeChanged.connect(self._auto_scale_y)
        self.layout.addWidget(self.chart_widget)

        self.indicator_widgets = []

        # # Volume chart with date axis
        # volume_date_axis = pg.DateAxisItem(orientation='bottom')
        # self.volume_widget = PlotWidget(
        #     viewBox=CustomViewBox(),
        #     axisItems={'bottom': volume_date_axis}
        # )
        # self.volume_widget.setMaximumHeight(150)
        # self.volume_widget.setStyleSheet("border: none;")
        # self.layout.addWidget(self.volume_widget)
        # self.volume_widget.setXLink(self.chart_widget)

        self.apply_stylesheet()

        # Connect X range changes to auto-scale Y axis

        # # Status label
        # self.status_label = QLabel("No price file loaded")
        # self.layout.addWidget(self.status_label)
    
    @property
    def price_file(self):
        return find_attribute(self, 'h5_file')
    
    def build_indicator_plots(self):
        clear_layout(self.layout, skip_count=2)
        for indicator_widget in self.indicator_widgets:
            pass


    def _auto_scale_y(self):
        """Auto-scale Y axis to fit data visible in current X range."""
        import pyqtgraph as pg

        vb = self.chart_widget.getPlotItem().getViewBox()
        x_min, x_max = vb.viewRange()[0]

        # Find the wick curve which contains all price data (lows and highs)
        wick_curve = None
        for item in self.chart_widget.getPlotItem().items:
            if isinstance(item, pg.PlotCurveItem):
                wick_curve = item
                break

        if wick_curve is None:
            return

        x_data, y_data = wick_curve.getData()
        if x_data is None or len(x_data) == 0:
            return

        # Filter to visible X range
        mask = (x_data >= x_min) & (x_data <= x_max)
        visible_y = y_data[mask]

        if len(visible_y) == 0:
            return

        y_min, y_max = visible_y.min(), visible_y.max()
        padding = (y_max - y_min) * 0.05 if y_max > y_min else y_max * 0.05

        vb.setYRange(y_min - padding, y_max + padding, padding=0)

    def load(self):
        """Load available intervals from PriceFile into the timeframe combo."""
        with block_signals(self.timeframe_combo):
            self.timeframe_combo.clear()

            if not self.price_file:
                # self.status_label.setText("No price file loaded")
                return

            intervals = self.price_file.get_available_intervals()
            for interval_seconds, label in intervals.items():
                self.timeframe_combo.addItem(label, interval_seconds)

            # self.status_label.setText(f"Loaded {len(intervals)} intervals")
            self.update_chart()

    def clear_chart(self):
        """Clear all chart data."""
        self.chart_widget.clear()
        # self.volume_widget.clear()

    def update_chart(self):
        interval = self.timeframe_combo.currentData()
        if interval is None:
            return

        if not self.price_file:
            return

        dataset, _ = self.price_file.get_interval_data(interval)
        if dataset is None or len(dataset) == 0:
            return

        vb = self.chart_widget.getPlotItem().getViewBox()
        prev_x_range = vb.viewRange()[0]

        timestamps = dataset['unix'].astype(np.float64)
        opens = dataset['open'].astype(np.float64)
        highs = dataset['high'].astype(np.float64)
        lows = dataset['low'].astype(np.float64)
        closes = dataset['close'].astype(np.float64)

        self.clear_chart()
        self.plot_candlesticks(timestamps, opens, highs, lows, closes, interval)

        # Restore X range if it overlaps with data (preserves view when switching intervals)
        if prev_x_range is not None:
            data_min, data_max = timestamps[0], timestamps[-1]
            x_min, x_max = prev_x_range
            if x_min < data_max and x_max > data_min:
                vb.setXRange(x_min, x_max, padding=0)
                self._auto_scale_y()
       
    def plot_candlesticks(self, timestamps, opens, highs, lows, closes, interval=None):
        import pyqtgraph as pg

        n = len(timestamps)
        if n == 0:
            return

        # Use interval directly for candle width if provided, otherwise calculate from data
        if interval is not None:
            candle_width = float(interval) * 0.8
        elif n > 1:
            deltas = np.diff(timestamps)
            candle_width = float(np.median(deltas)) * 0.8
        else:
            candle_width = 60.0 * 0.8  # default 1 minute

        ts, op, hi, lo, cl = timestamps, opens, highs, lows, closes

        n_display = len(ts)

        # Determine colors: green for bullish, red for bearish
        bullish = cl >= op

        green = pg.mkColor('#26a69a')
        red = pg.mkColor('#ef5350')

        # Build candle bodies using BarGraphItem (efficient batch rendering)
        body_heights = np.abs(cl - op)
        body_bottoms = np.minimum(op, cl)

        # Separate bullish and bearish for different colors
        bull_mask = bullish
        bear_mask = ~bullish

        # Bullish candles (green)
        if np.any(bull_mask):
            bull_bars = pg.BarGraphItem(
                x=ts[bull_mask],
                height=body_heights[bull_mask],
                width=candle_width,
                y0=body_bottoms[bull_mask],
                brush=green,
                pen=pg.mkPen(green, width=1)
            )
            self.chart_widget.addItem(bull_bars)

        # Bearish candles (red)
        if np.any(bear_mask):
            bear_bars = pg.BarGraphItem(
                x=ts[bear_mask],
                height=body_heights[bear_mask],
                width=candle_width,
                y0=body_bottoms[bear_mask],
                brush=red,
                pen=pg.mkPen(red, width=1)
            )
            self.chart_widget.addItem(bear_bars)

        # Build wicks as line segments
        # Each wick needs 2 segments: low-to-body_bottom and body_top-to-high
        # Use connect='pairs' mode for efficiency
        wick_x = np.empty(n_display * 4, dtype=np.float64)
        wick_y = np.empty(n_display * 4, dtype=np.float64)
        wick_connect = np.zeros(n_display * 4, dtype=np.int32)

        body_tops = np.maximum(op, cl)

        # Lower wick: (ts, low) -> (ts, body_bottom)
        wick_x[0::4] = ts
        wick_y[0::4] = lo
        wick_x[1::4] = ts
        wick_y[1::4] = body_bottoms
        wick_connect[0::4] = 1  # connect to next point

        # Upper wick: (ts, body_top) -> (ts, high)
        wick_x[2::4] = ts
        wick_y[2::4] = body_tops
        wick_x[3::4] = ts
        wick_y[3::4] = hi
        wick_connect[2::4] = 1  # connect to next point

        wick_pen = pg.mkPen(color='#888888', width=1)
        wick_curve = pg.PlotCurveItem(
            x=wick_x,
            y=wick_y,
            connect=wick_connect,
            pen=wick_pen
        )
        self.chart_widget.addItem(wick_curve)

        # Manually set ranges (BarGraphItem doesn't report bounds for autoRange)
        price_min, price_max = lo.min(), hi.max()
        price_padding = (price_max - price_min) * 0.05
        time_padding = (ts[-1] - ts[0]) * 0.02

        vb = self.chart_widget.getPlotItem().getViewBox()
        vb.disableAutoRange()
        vb.setRange(
            xRange=(ts[0] - time_padding, ts[-1] + time_padding),
            yRange=(price_min - price_padding, price_max + price_padding),
            padding=0
        )

    def apply_stylesheet(self):
        """Apply stylesheet to the chart."""
        from gui.style import TEXT_COLOR

        text_color = QColor(TEXT_COLOR)
        half_text_color = QColor(apply_alpha_to_hex(TEXT_COLOR, 0.5))
        transparent_bg = '#00000000'

        self.chart_widget.setBackground(transparent_bg)
        self.chart_widget.getAxis('left').setPen(half_text_color)
        self.chart_widget.getAxis('bottom').setPen(half_text_color)
        self.chart_widget.getAxis('left').setTextPen(text_color)
        self.chart_widget.getAxis('bottom').setTextPen(text_color)
        self.chart_widget.setLabel('left', 'Price', color=text_color)
        self.chart_widget.setLabel('bottom', 'Time', color=text_color)
        self.chart_widget.showGrid(x=True, y=True, alpha=0.15)

        # self.volume_widget.setBackground(transparent_bg)
        # self.volume_widget.getAxis('left').setPen(half_text_color)
        # self.volume_widget.getAxis('bottom').setPen(half_text_color)
        # self.volume_widget.getAxis('left').setTextPen(text_color)
        # self.volume_widget.getAxis('bottom').setTextPen(text_color)
        # self.volume_widget.setLabel('left', 'Volume', color=text_color)
        # self.volume_widget.showGrid(x=True, y=True, alpha=0.15)
