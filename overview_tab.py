# dashboard/overview_tab.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Modern Color Scheme
COLORS = {
    "header": "#3d87ff",        # Deep Blue
    "primary": "#283593",       # Dark Blue
    "secondary": "#5C6BC0",     # Medium Blue
    "accent": "#FF5722",        # Orange
    "positive": "#4CAF50",      # Green
    "negative": "#D32F2F",      # Red
    "background": "#11425E",    # Light Gray
    "text_dark": "#080705",     # Dark Gray
    "text_light": "#000000",    # White
    "highlight": "#FFD700"      # Gold
}

def create_metric_card(title, value, help_text, color=COLORS["primary"], icon="📊", delta=None):
    """Modern metric card with adaptive colors"""
    text_color = COLORS["text_light"] if color in [COLORS["primary"], COLORS["negative"], COLORS["positive"]] else COLORS["text_dark"]
    return f"""
    <div style="
        background: {color};
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 0.5rem;
        color: {text_color};
    ">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">{icon}</div>
            <div>
                <h3 style="margin: 0 0 0.25rem 0; font-size: 1.1rem;">
                    {title}
                </h3>
                <div style="font-size: 1.75rem; font-weight: 700;">
                    {value}{delta if delta else ''}
                </div>
                <div style="font-size: 0.9rem; opacity: 0.9;">
                    {help_text}
                </div>
            </div>
        </div>
    </div>
    """

def overview_tab():
    """Modern Inventory Overview Dashboard"""
    try:
        # ==================== HEADER ====================
        st.markdown(f"""
        <div style="
            background: {COLORS["header"]};
            padding: 2.5rem;
            border-radius: 15px;
            color: {COLORS["text_light"]};
            margin-bottom: 2rem;
        ">
            <div style="max-width: 1200px; margin: 0 auto;">
                <h1 style="margin:0; font-size: 2.5rem;">Supply Chain Intelligence</h1>
                <p style="margin:0.5rem 0 0 0; font-size: 1.1rem;">
                    Holistic view of inventory health, supplier performance, and operational efficiency
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ==================== DATA LOADING ====================
        loader = st.session_state.data_loader
        merged = loader.get_merged_ledger()
        
        if merged.empty:
            st.warning("No operational data available")
            return

        # ==================== INTERACTIVE CONTROLS ====================
        with st.expander("⚙️ Dashboard Controls", expanded=True):
            cols = st.columns(3)
            with cols[0]:
                date_range = st.date_input(
                    "Reporting Period",
                    value=[merged['date'].min().date(), merged['date'].max().date()]
                )
            with cols[1]:
                selected_product = st.selectbox(
                    "Focus Product",
                    merged['product_id'].unique()
                )
            with cols[2]:
                view_mode = st.radio(
                    "View Mode",
                    ["Overview"],
                    horizontal=True
                )

        # Data Filtering
        start_dt = pd.to_datetime(date_range[0])
        end_dt = pd.to_datetime(date_range[1])
        filtered = merged[
            (merged['date'] >= start_dt) & 
            (merged['date'] <= end_dt) &
            (merged['product_id'] == selected_product)
        ].copy()

        # ==================== CORE METRICS ====================
        st.markdown("""
        <div style="margin: 2rem 0 1rem 0;">
            <h2 style="color: #faf9f5; border-bottom: 2px solid #5C6BC0; 
                padding-bottom: 0.5rem; font-size: 1.4rem;">
                Key Performance Indicators
            </h2>
        </div>
        """, unsafe_allow_html=True)

        # Calculate Advanced Metrics
        service_level = 1 - (filtered['unmet_demand'].sum() / filtered['demand'].sum())
        supplier_risk_score = (filtered['lead_time'] * (100 - filtered['reliability'])).mean() / 100
        avg_lead_time = filtered['lead_time'].mean()
        order_efficiency = ((filtered['restocked_qty'] >= filtered['MOQ']) & 
                    (filtered['lead_time'] <= filtered['lead_time'].quantile(0.75))).mean()


        cols = st.columns(3)
        with cols[0]:
            st.markdown(create_metric_card(
                "Avg Lead Time",
                f"{avg_lead_time:.1f}d",
                "Supplier responsiveness",
                COLORS["secondary"],
                "⏱️",
                delta="▲ 2d" if avg_lead_time > 7 else "▼ 1d"
            ), unsafe_allow_html=True)
        
        with cols[1]:
            st.markdown(create_metric_card(
                "Service Level",
                f"{service_level:.0%}",
                "Demand fulfillment",
                COLORS["positive"] if service_level > 0.9 else COLORS["negative"],
                "✅"
            ), unsafe_allow_html=True)

        with cols[2]:
            st.markdown(create_metric_card(
                "Supplier Risk",
                f"{supplier_risk_score:.1f}",
                "Lower is better",
                COLORS["negative"] if supplier_risk_score > 5 else COLORS["positive"],
                "⚠️"
            ), unsafe_allow_html=True)

        '''with cols[3]:
            st.markdown(create_metric_card(
                "Order Efficiency",
                f"{order_efficiency:.0%}",
                "MOQ + Lead Time",
                COLORS["accent"],
                "⚡"
            ), unsafe_allow_html=True)'''

        # ==================== INVENTORY HEALTH ====================
        st.markdown("""
        <div style="margin: 3rem 0 1rem 0;">
            <h2 style="color: #faf9f5; border-bottom: 2px solid #5C6BC0; 
                padding-bottom: 0.5rem; font-size: 1.4rem;">
                Inventory Health Timeline
            </h2>
        </div>
        """, unsafe_allow_html=True)

        fig = px.area(
            filtered,
            x='date',
            y='closing_stock',
            title=f"{selected_product} Stock Position",
            labels={'closing_stock': 'Units Available'},
            color_discrete_sequence=[COLORS["secondary"]]
        )
        fig.add_hrect(
            y0=0,
            y1=filtered['safety_stock'].mean(),
            fillcolor=COLORS["negative"],
            opacity=0.1,
            annotation_text="Safety Threshold", 
            annotation_position="top left"
        )
        fig.update_layout(
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"],
            font_color=COLORS["text_dark"],
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # ==================== SUPPLIER PERFORMANCE MATRIX ====================
        st.markdown("""
        <div style="margin: 3rem 0 1rem 0;">
            <h2 style="color: #faf9f5; border-bottom: 2px solid #5C6BC0; 
                padding-bottom: 0.5rem; font-size: 1.4rem;">
                Supplier Performance Matrix
            </h2>
        </div>
        """, unsafe_allow_html=True)

        supplier_stats = merged.groupby('supplier_id').agg(
            num_products=('products', 'nunique'),
            product_list=('products', lambda x: ', '.join(sorted(x.unique()))),
            lead_time=('lead_time', 'mean'),
            reliability=('reliability', 'mean'),
            MOQ=('MOQ', 'mean')
        ).reset_index()

        fig = px.treemap(
            supplier_stats,
            path=['supplier_id'],
            values='num_products',
            color='lead_time',
            color_continuous_scale='RdYlGn_r',
            hover_data= ['product_list','reliability', 'MOQ'],
            title="Supplier Network Analysis",
            labels={
                'lead_time': 'Avg Lead Time',
                'reliability': 'Reliability %',
                'MOQ': 'Min Order Qty'
            }
        )
        fig.update_layout(
            margin=dict(t=50, l=25, r=25, b=25),
            coloraxis_colorbar=dict(
                title="Lead Time (Days)",
                tickvals=[supplier_stats['lead_time'].min(), supplier_stats['lead_time'].max()],
                ticktext=["Fast", "Slow"]
            )
        )
        fig.update_traces(
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>%{value} products<br>%{color:.1f} days",
            marker=dict(line=dict(color=COLORS["background"], width=2))
        )
        st.plotly_chart(fig, use_container_width=True)

        # ==================== ORDER INTELLIGENCE ====================
        st.markdown("""
        <div style="margin: 3rem 0 1rem 0;">
            <h2 style="color: #faf9f5; border-bottom: 2px solid #5C6BC0; 
                padding-bottom: 0.5rem; font-size: 1.4rem;">
                Order Intelligence
            </h2>
        </div>
        """, unsafe_allow_html=True)

        order_analysis = merged.groupby('supplier_id').agg({
            'restocked_qty': 'sum',
            'lead_time': 'mean',
            'reliability': 'mean'
        }).reset_index()

        fig = px.bar(
            order_analysis,
            x='supplier_id',
            y='restocked_qty',
            color='lead_time',
            color_continuous_scale=px.colors.sequential.Magma,
            labels={'restocked_qty': 'Total Units Ordered'},
            text_auto='.2s'
        )
        fig.update_layout(
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"],
            font_color=COLORS["text_dark"],
            xaxis_title="Supplier",
            yaxis_title="Total Orders",
            coloraxis_colorbar=dict(
                title="Lead Time (Days)",
                orientation="h",
                yanchor="bottom",
                y=-0.5
            )
        )
        fig.update_traces(
            textfont_color=COLORS["text_light"],
            marker_line_color=COLORS["text_dark"],
            marker_line_width=1.5
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"System error: {str(e)}")
        st.markdown(f"""
            <div style="
                background: #FFEBEE;
                padding: 1.5rem;
                border-radius: 10px;
                margin-top: 1rem;
            ">
                <h4 style="color: {COLORS["negative"]}; margin: 0 0 1rem 0;">
                    ⚠️ System Recovery Required
                </h4>
                <ol style="color: {COLORS["text_dark"]};">
                    <li>Refresh application</li>
                    <li>Verify data files in /data directory</li>
                    <li>Contact supplychain-support@company.com</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    overview_tab()