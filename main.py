
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.core.window import Window

Window.clearcolor = (0.08, 0.09, 0.11, 1)

# --- Technical Indicator Calculations ---
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = [prices[0]]
    for price in prices[1:]:
        ema.append((price * k) + (ema[-1] * (1 - k)))
    return ema

def calculate_psar(highs, lows, af_start=0.02, af_max=0.04):
    if len(highs) < 2:
        return lows
    psar = [lows[0]]
    bull = True
    af = af_start
    ep = highs[0]

    for i in range(1, len(highs)):
        prev_psar = psar[-1]
        if bull:
            cur_psar = prev_psar + af * (ep - prev_psar)
            cur_psar = min(cur_psar, lows[i-1], lows[max(0, i-2)])
            if lows[i] < cur_psar:
                bull = False
                cur_psar = ep
                ep = lows[i]
                af = af_start
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_start, af_max)
        else:
            cur_psar = prev_psar + af * (ep - prev_psar)
            cur_psar = max(cur_psar, highs[i-1], highs[max(0, i-2)])
            if highs[i] > cur_psar:
                bull = True
                cur_psar = ep
                ep = highs[i]
                af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = max(af - af_start, af_max)
        psar.append(cur_psar)
    return psar

# --- Chart Canvas Widget ---
class IndicatorChart(Widget):
    def draw_chart(self, prices):
        self.canvas.clear()
        if len(prices) < 2:
            return

        w, h = self.width, self.height
        pad = 20
        min_p, max_p = min(prices), max(prices)
        p_range = max_p - min_p if max_p != min_p else 1

        def get_y(val):
            return pad + ((val - min_p) / p_range) * (h - 2 * pad)

        def get_x(idx):
            return pad + (idx / (len(prices) - 1)) * (w - 2 * pad)

        # 1. Support & Resistance Lines
        with self.canvas:
            Color(0, 0.8, 0.4, 0.6) # Support (Green Line)
            Line(points=[pad, get_y(min_p), w - pad, get_y(min_p)], width=1.5, dash_offset=5)
            Color(1, 0.2, 0.3, 0.6) # Resistance (Red Line)
            Line(points=[pad, get_y(max_p), w - pad, get_y(max_p)], width=1.5, dash_offset=5)

        # 2. EMAs Drawing
        ema5 = calculate_ema(prices, 5)
        ema13 = calculate_ema(prices, 13)
        ema55 = calculate_ema(prices, 55)

        for ema_vals, color in [(ema5, (1, 0.8, 0, 1)), (ema13, (0, 0.7, 1, 1)), (ema55, (0.8, 0.2, 1, 1))]:
            pts = []
            for i, val in enumerate(ema_vals):
                pts.extend([get_x(i), get_y(val)])
            with self.canvas:
                Color(*color)
                Line(points=pts, width=1.5)

        # 3. Parabolic SAR Dots
        psar = calculate_psar(prices, prices, 0.02, 0.04)
        with self.canvas:
            Color(1, 1, 1, 0.8)
            for i, val in enumerate(psar):
                cx, cy = get_x(i), get_y(val)
                Rectangle(pos=(cx - 2, cy - 2), size=(4, 4))

        # 4. Price Line
        pts = []
        for i, val in enumerate(prices):
            pts.extend([get_x(i), get_y(val)])
        with self.canvas:
            Color(1, 1, 1, 0.3)
            Line(points=pts, width=1)

# --- Main App Layout ---
class SignalApp(BoxLayout):
    def __init__(self, **kwargs):
        super(SignalApp, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 15
        self.spacing = 10

        self.add_widget(Label(
            text="[b]Technical Indicator Chart & Signal[/b]", 
            markup=True, font_size='18sp', size_hint_y=None, height=40
        ))

        self.price_input = TextInput(
            text="1.1325, 1.1320, 1.1318, 1.1315, 1.1310, 1.1302, 1.1304, 1.1308, 1.1312, 1.1315",
            multiline=False, size_hint_y=None, height=40
        )
        self.add_widget(self.price_input)

        self.chart = IndicatorChart()
        self.add_widget(self.chart)

        self.btn = Button(
            text="GENERATE SIGNAL & CHART", background_color=(0.1, 0.5, 0.9, 1),
            font_size='15sp', bold=True, size_hint_y=None, height=45
        )
        self.btn.bind(on_press=self.process_signal)
        self.add_widget(self.btn)

        self.result_label = Label(
            text="Signal: READY", font_size='18sp', bold=True, color=(1, 1, 1, 1),
            size_hint_y=None, height=50
        )
        self.add_widget(self.result_label)

    def process_signal(self, instance):
        try:
            prices = [float(x.strip()) for x in self.price_input.text.split(',')]
            if len(prices) < 5:
                self.result_label.text = "Error: Min 5 prices needed"
                return

            self.chart.draw_chart(prices)

            e5 = calculate_ema(prices, 5)[-1]
            e13 = calculate_ema(prices, 13)[-1]
            e55 = calculate_ema(prices, 55)[-1]
            psar_last = calculate_psar(prices, prices, 0.02, 0.04)[-1]
            curr_p = prices[-1]

            # Signal Logic Combine
            buy_score = 0
            sell_score = 0

            if e5 > e13: buy_score += 1
            else: sell_score += 1

            if e13 > e55: buy_score += 1
            else: sell_score += 1

            if curr_p > psar_last: buy_score += 1
            else: sell_score += 1

            if buy_score >= 2:
                signal, color = "STRONG BUY (CALL) ▲", (0.2, 0.9, 0.4, 1)
            elif sell_score >= 2:
                signal, color = "STRONG SELL (PUT) ▼", (1, 0.3, 0.3, 1)
            else:
                signal, color = "HOLD / NEUTRAL ⏸", (0.9, 0.9, 0.2, 1)

            self.result_label.text = f"Signal: {signal}\\nPrice: {curr_p}"
            self.result_label.color = color

        except Exception:
            self.result_label.text = "Invalid Input Data"
            self.result_label.color = (1, 0.3, 0.3, 1)

class MainApp(App):
    def build(self):
        return SignalApp()

if __name__ == '__main__':
    MainApp().run()


