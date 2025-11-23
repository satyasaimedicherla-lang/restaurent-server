import flet as ft
import requests
import threading
import time
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
# ⚠️ REPLACE THIS with your actual Render URL after deploying Step 3
SERVER_URL = "https://YOUR-APP-NAME.onrender.com" 
DATA_ENDPOINT = f"{SERVER_URL}/data"

# --- Palette ---
COLOR_SIDEBAR_BG = "#1E1E2E"
COLOR_SIDEBAR_ACTIVE = "#3D3D5C"
COLOR_MAIN_BG = "#F4F7FE"
COLOR_CARD_BG = "#FFFFFF"
COLOR_TEXT_PRIMARY = "#2B3674"
COLOR_TEXT_SECONDARY = "#A3AED0"
COLOR_ACCENT = "#4318FF"
COLOR_SUCCESS = "#05CD99"
COLOR_WARNING = "#FFB547"
COLOR_DANGER = "#EE5D50"

# --- HELPER: Manual Opacity Function ---
def get_opacity_color(color_hex, opacity):
    try:
        hex_code = color_hex.lstrip('#')
        alpha = int(opacity * 255)
        return f"#{alpha:02x}{hex_code}"
    except:
        return color_hex

def main(page: ft.Page):
    page.title = "Smart Restaurant Ops"
    page.padding = 0
    page.bgcolor = COLOR_MAIN_BG
    page.theme_mode = ft.ThemeMode.LIGHT

    # ================= UI COMPONENTS =================

    # --- Sidebar ---
    def change_page(e):
        sel_idx = e.control.selected_index
        if sel_idx == 0:
            content_area.content = dashboard_view
        elif sel_idx == 1:
            content_area.content = live_monitor_view
        page.update()

    sidebar = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        bgcolor=COLOR_SIDEBAR_BG,
        indicator_color=COLOR_SIDEBAR_ACTIVE,
        on_change=change_page,
        destinations=[
            ft.NavigationRailDestination(
                icon="dashboard",  
                label="Dashboard", 
                padding=ft.padding.only(top=20)
            ),
            ft.NavigationRailDestination(
                icon="monitor_heart", 
                label="Live Monitor"
            ),
        ]
    )
    
    # --- KPI Card Creator ---
    def create_kpi(title, icon, value_ref, color=COLOR_ACCENT):
        bg_tint = get_opacity_color(color, 0.1)
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color=COLOR_TEXT_SECONDARY, weight="w500"),
                ft.Row([
                    ft.Container(
                        content=ft.Text(icon, size=20),
                        padding=10, 
                        bgcolor=bg_tint,
                        border_radius=30
                    ),
                    ft.Text(value="0", ref=value_ref, size=24, weight="bold", color=COLOR_TEXT_PRIMARY)
                ], alignment="spaceBetween")
            ]),
            bgcolor=COLOR_CARD_BG, padding=15, border_radius=15,
            expand=True, 
            shadow=ft.BoxShadow(blur_radius=10, color="#0D000000")
        )

    # --- Live Grid Creator ---
    live_grid = ft.GridView(
        expand=True, runs_count=2, max_extent=200, child_aspect_ratio=1.3,
        spacing=10, run_spacing=10
    )

    # --- Charts ---
    chart_data_points = [ft.LineChartDataPoint(i, 0) for i in range(24)]
    chart_fill_color = get_opacity_color(COLOR_ACCENT, 0.2)

    line_chart = ft.LineChart(
        data_series=[
            ft.LineChartData(
                data_points=chart_data_points,
                stroke_width=3,
                color=COLOR_ACCENT,
                below_line_bgcolor=chart_fill_color,
                curved=True
            )
        ],
        border=ft.border.all(0, ft.Colors.TRANSPARENT),
        left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Calls")),
        bottom_axis=ft.ChartAxis(labels_size=20, title=ft.Text("Hour")),
        tooltip_bgcolor=COLOR_SIDEBAR_BG,
        min_y=0, max_y=10,
        expand=True
    )

    pie_chart = ft.PieChart(
        sections=[
            ft.PieChartSection(1, color=COLOR_DANGER, radius=40),
            ft.PieChartSection(1, color=COLOR_SUCCESS, radius=40)
        ],
        sections_space=0, center_space_radius=30, expand=True
    )

    # --- Mutable References ---
    val_total = ft.Ref[ft.Text]()
    val_open = ft.Ref[ft.Text]()
    val_resp = ft.Ref[ft.Text]()
    val_dlv = ft.Ref[ft.Text]()
    txt_time = ft.Ref[ft.Text]()

    # --- Views ---
    
    # 1. Dashboard View
    dashboard_view = ft.Column([
        ft.Row([
            ft.Column([
                ft.Text("Welcome, M. Satya Sai", color=COLOR_TEXT_SECONDARY, size=14),
                ft.Text("Dashboard Overview", color=COLOR_TEXT_PRIMARY, size=28, weight="bold")
            ]),
            ft.Text(ref=txt_time, color=COLOR_ACCENT, size=16, weight="bold")
        ], alignment="spaceBetween"),
        
        ft.Divider(height=20, color="transparent"),
        
        ft.Row([
            create_kpi("Total Calls", "📞", val_total, COLOR_ACCENT),
            create_kpi("Active", "🔥", val_open, COLOR_DANGER),
            create_kpi("Avg Resp", "⏱️", val_resp, COLOR_WARNING),
            create_kpi("Avg Dlv", "🍽️", val_dlv, COLOR_SUCCESS),
        ]),

        ft.Divider(height=20, color="transparent"),

        ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text("Live Floor Status", size=18, weight="bold", color=COLOR_TEXT_PRIMARY),
                    live_grid
                ]),
                expand=2, bgcolor=COLOR_CARD_BG, border_radius=15, padding=15
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Traffic (Hourly)", weight="bold", color=COLOR_TEXT_PRIMARY),
                    ft.Container(line_chart, height=150),
                    ft.Divider(),
                    ft.Text("Request Mix", weight="bold", color=COLOR_TEXT_PRIMARY),
                    ft.Container(pie_chart, height=150)
                ]),
                expand=1, bgcolor=COLOR_CARD_BG, border_radius=15, padding=15
            )
        ], expand=True)
    ], expand=True, scroll=ft.ScrollMode.HIDDEN)

    # 2. Live Monitor View
    live_monitor_view = ft.Column([
        ft.Text("Live Floor Monitor", size=28, weight="bold", color=COLOR_TEXT_PRIMARY),
        ft.Container(
            content=live_grid, 
            expand=True, bgcolor=COLOR_CARD_BG, border_radius=15, padding=20
        )
    ], expand=True)

    content_area = ft.Container(content=dashboard_view, expand=True, padding=20)
    
    page.add(
        ft.Row([
            sidebar,
            ft.VerticalDivider(width=1, color="transparent"),
            content_area
        ], expand=True)
    )

    # ================= LOGIC & UPDATES =================

    def update_clock():
        while True:
            if txt_time.current:
                txt_time.current.value = datetime.now().strftime("%I:%M:%S %p")
                page.update()
            time.sleep(1)

    def fetch_data_loop():
        while True:
            try:
                # Use verify=False if you have SSL certificate issues on some networks
                r = requests.get(DATA_ENDPOINT, timeout=10) 
                
                if r.status_code == 200:
                    data = r.json()
                    anl = data.get('analytics', {})
                    
                    if val_total.current: val_total.current.value = anl.get('total', '0')
                    if val_open.current: val_open.current.value = anl.get('open', '0')
                    if val_resp.current: val_resp.current.value = anl.get('avg_resp', '0.0') + "m"
                    if val_dlv.current: val_dlv.current.value = anl.get('avg_dlv', '0.0') + "m"

                    hourly = anl.get('hourly', {})
                    max_val = 0
                    for i in range(24):
                        val = hourly.get(str(i), 0)
                        if val > max_val: max_val = val
                        chart_data_points[i].y = val
                    line_chart.max_y = max_val + 2

                    open_c = int(anl.get('open', 0))
                    closed_c = int(anl.get('closed', 0))
                    pie_chart.sections[0].value = open_c
                    pie_chart.sections[1].value = closed_c
                    if open_c + closed_c == 0:
                         pie_chart.sections[0].value = 0.1

                    live_data = data.get('live_status', [])
                    new_controls = []
                    for item in live_data:
                        tid = item['table_id']
                        status = item['status']
                        mins = item['minutes_ago']
                        
                        bg = "#F8F9FB"
                        border = "transparent"
                        icon = "✨"
                        txt_col = COLOR_SUCCESS
                        status_txt = "Available"

                        if status == "Customer_Called":
                            bg = "#FFF5F5"; border = COLOR_DANGER; icon = "🔔"; txt_col = COLOR_DANGER; status_txt = "NEEDS SERVICE"
                        elif status == "Waiter_Responded":
                            bg = "#FFFBF0"; border = COLOR_WARNING; icon = "👨‍🍳"; txt_col = COLOR_WARNING; status_txt = "ATTENDING"
                        elif status == "Idle":
                            status_txt = "AVAILABLE"
                        
                        new_controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Text(f"T-{tid}", weight="bold", size=16, color=COLOR_TEXT_PRIMARY),
                                        ft.Text(f"{mins}m", size=10, color=COLOR_TEXT_SECONDARY)
                                    ], alignment="spaceBetween"),
                                    ft.Text(icon, size=30),
                                    ft.Text(status_txt, color=txt_col, weight="bold", size=11)
                                ], alignment="center", horizontal_alignment="center"),
                                bgcolor=bg,
                                border=ft.border.all(2, border) if border != "transparent" else None,
                                border_radius=10, padding=10,
                                shadow=ft.BoxShadow(blur_radius=5, color="#0D000000")
                            )
                        )
                    live_grid.controls = new_controls
                    page.update()

            except Exception as e:
                print(f"Error fetching data: {e}")
            
            time.sleep(3) # Increased sleep time for cloud server politeness

    threading.Thread(target=update_clock, daemon=True).start()
    threading.Thread(target=fetch_data_loop, daemon=True).start()

ft.app(target=main)