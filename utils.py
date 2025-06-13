# dashboard/utils.py
import plotly.graph_objects as go

def format_number(n):
    return f"{int(n):,}"

def get_forecast_sparkline(forecast_df, product_id):
    df = forecast_df[forecast_df["product_id"] == product_id].sort_values("date")
    fig = go.Figure(go.Scatter(
        x=df["date"], y=df["predicted_units"], mode="lines+markers",
        line=dict(color="dodgerblue"), name="Forecast"
    ))
    fig.update_layout(
        title=f"{product_id} - Next 7 Days Forecast",
        margin=dict(l=10, r=10, t=40, b=10),
        height=200
    )
    return fig

