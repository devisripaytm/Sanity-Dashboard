"""
OCL Dataset Validation Dashboard
A comprehensive Streamlit dashboard for visualizing OCL dataset validation results.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import re
from datetime import datetime

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="OCL Validation Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# COLOR SCHEME
# =============================================================================
COLORS = {
    "ok": "#10B981",           # Emerald green
    "partial_ok": "#F59E0B",   # Amber
    "not_ok": "#EF4444",       # Red
    "primary": "#3B82F6",      # Blue
    "secondary": "#6B7280",    # Gray
    "background": "#1F2937",   # Dark gray
    "surface": "#374151",      # Medium gray
    "text": "#F9FAFB"          # Light gray
}

CASE_COLORS = px.colors.qualitative.Set3

# =============================================================================
# CUSTOM CSS
# =============================================================================
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #0d1b2a 100%);
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 8px 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-icon {
        font-size: 2rem;
        margin-bottom: 8px;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(30, 41, 59, 0.8);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3B82F6;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #F9FAFB !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: rgba(51, 65, 85, 0.5);
        border-radius: 12px;
        padding: 16px;
        border: 2px dashed rgba(59, 130, 246, 0.5);
    }
    
    /* Success/warning badges */
    .success-badge {
        background-color: #10B981;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .warning-badge {
        background-color: #F59E0B;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .error-badge {
        background-color: #EF4444;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    /* DataFrame styling */
    .dataframe {
        font-size: 0.85rem;
    }
    
    /* Filter section */
    .filter-section {
        background-color: rgba(30, 41, 59, 0.6);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(90deg, #2563EB, #7C3AED);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_case_number(sanity_reason):
    """Extract case number from sanity reason string."""
    if pd.isna(sanity_reason):
        return "Unknown"
    match = re.search(r'Case\s*(\d+)', str(sanity_reason))
    return f"Case {match.group(1)}" if match else "Unknown"


def get_unique_dataset_count(df, id_column="Dataset ID"):
    """Get unique dataset count from dataframe."""
    if df is None or df.empty:
        return 0
    return df[id_column].nunique()


def create_metric_card(icon, label, value, color):
    """Create a styled metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value" style="color: {color};">{value:,}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def create_percentage_card(icon, label, value, color):
    """Create a styled percentage metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value" style="color: {color};">{value:.1f}%</div>
        <div class="metric-label">{label}</div>
    </div>
    """


@st.cache_data
def convert_df_to_csv(df):
    """Convert DataFrame to CSV for download."""
    return df.to_csv(index=False).encode('utf-8')


def convert_dfs_to_excel(dfs_dict):
    """Convert multiple DataFrames to Excel with multiple sheets."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs_dict.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    output.seek(0)
    return output


def apply_filters(df, filters_dict):
    """Apply multiple filters to a DataFrame."""
    filtered_df = df.copy()
    for column, values in filters_dict.items():
        if values and column in filtered_df.columns:
            if isinstance(values, list):
                filtered_df = filtered_df[filtered_df[column].isin(values)]
            else:
                filtered_df = filtered_df[filtered_df[column] == values]
    return filtered_df


def search_dataset(df, search_term, id_column="Dataset ID"):
    """Search for dataset by ID."""
    if not search_term:
        return df
    search_term = str(search_term).strip()
    return df[df[id_column].astype(str).str.contains(search_term, case=False, na=False)]


def get_sanity_run_date(df):
    """Extract sanity run date from DataFrame."""
    date_cols = ['sanity run date', 'sanity_run_date', 'Sanity run date']
    for col in date_cols:
        if col in df.columns:
            dates = df[col].dropna()
            if not dates.empty:
                return dates.iloc[0]
    return "N/A"


# =============================================================================
# CHART FUNCTIONS
# =============================================================================

def create_distribution_pie(ok_count, partial_count, not_ok_count):
    """Create pie chart for OK/Partial/Not OK distribution."""
    fig = go.Figure(data=[go.Pie(
        labels=['OK', 'Partial OK', 'Not OK'],
        values=[ok_count, partial_count, not_ok_count],
        hole=0.5,
        marker_colors=[COLORS['ok'], COLORS['partial_ok'], COLORS['not_ok']],
        textinfo='label+percent',
        textfont_size=14,
        textfont_color='white',
        hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Percentage: %{percent}<extra></extra>"
    )])
    
    fig.update_layout(
        title=dict(text="Validation Results Distribution", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        annotations=[dict(
            text=f'{ok_count + partial_count + not_ok_count:,}<br>Total',
            x=0.5, y=0.5,
            font_size=16,
            font_color='white',
            showarrow=False
        )]
    )
    return fig


def create_case_distribution_bar(df, case_column='Sanity reason'):
    """Create bar chart for case distribution."""
    # Find the correct column name
    possible_cols = ['Sanity reason', 'sanity reason', 'sanity_reason', 'Sanity Reason']
    col_name = None
    for col in possible_cols:
        if col in df.columns:
            col_name = col
            break
    
    if col_name is None:
        return None
    
    df['Case'] = df[col_name].apply(extract_case_number)
    case_counts = df['Case'].value_counts().reset_index()
    case_counts.columns = ['Case', 'Count']
    case_counts = case_counts.sort_values('Case')
    
    fig = px.bar(
        case_counts,
        x='Case',
        y='Count',
        color='Case',
        color_discrete_sequence=CASE_COLORS,
        text='Count'
    )
    
    fig.update_traces(textposition='outside', textfont_size=12)
    fig.update_layout(
        title=dict(text="Case-wise Distribution", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title="Case", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="Count", gridcolor='rgba(255,255,255,0.1)'),
        showlegend=False
    )
    return fig


def create_ingest_type_bar(df_ok, df_partial, df_not_ok):
    """Create bar chart for ingest type distribution."""
    data = []
    
    for df, category in [(df_ok, 'OK'), (df_partial, 'Partial OK'), (df_not_ok, 'Not OK')]:
        if df is not None and not df.empty:
            # Find ingest type column
            ingest_col = None
            for col in ['Ingestion type', 'Ingest type', 'ingest_type']:
                if col in df.columns:
                    ingest_col = col
                    break
            
            if ingest_col:
                for ingest_type in df[ingest_col].unique():
                    count = len(df[df[ingest_col] == ingest_type]['Dataset ID'].unique())
                    data.append({'Category': category, 'Ingest Type': str(ingest_type), 'Count': count})
    
    if not data:
        return None
    
    chart_df = pd.DataFrame(data)
    
    fig = px.bar(
        chart_df,
        x='Category',
        y='Count',
        color='Ingest Type',
        barmode='group',
        color_discrete_sequence=[COLORS['primary'], COLORS['secondary']],
        text='Count'
    )
    
    fig.update_traces(textposition='outside', textfont_size=11)
    fig.update_layout(
        title=dict(text="Distribution by Ingest Type", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title="", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="Dataset Count", gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(title="Ingest Type")
    )
    return fig


def create_status_flag_pie(df_partial, df_not_ok):
    """Create pie chart for status flag distribution."""
    status_counts = {'Matching': 0, 'Unmatching': 0}
    
    for df in [df_partial, df_not_ok]:
        if df is not None and not df.empty:
            status_col = None
            for col in ['Status flag', 'status_flag', 'Status Flag']:
                if col in df.columns:
                    status_col = col
                    break
            
            if status_col:
                for status, count in df.groupby(status_col)['Dataset ID'].nunique().items():
                    status_str = str(status).strip()
                    if 'match' in status_str.lower():
                        if 'un' in status_str.lower() or 'not' in status_str.lower():
                            status_counts['Unmatching'] += count
                        else:
                            status_counts['Matching'] += count
    
    if sum(status_counts.values()) == 0:
        return None
    
    fig = go.Figure(data=[go.Pie(
        labels=list(status_counts.keys()),
        values=list(status_counts.values()),
        hole=0.4,
        marker_colors=[COLORS['ok'], COLORS['not_ok']],
        textinfo='label+percent',
        textfont_size=14,
        textfont_color='white'
    )])
    
    fig.update_layout(
        title=dict(text="Status Flag Distribution", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig


def create_max_date_bar(df_partial, df_not_ok):
    """Create bar chart for max date matching distribution."""
    data = []
    
    for df, category in [(df_partial, 'Partial OK'), (df_not_ok, 'Not OK')]:
        if df is not None and not df.empty:
            max_date_col = None
            for col in ['Max date not matching', 'max_date_matching', 'Max Date']:
                if col in df.columns:
                    max_date_col = col
                    break
            
            if max_date_col:
                for match_status in df[max_date_col].unique():
                    count = len(df[df[max_date_col] == match_status]['Dataset ID'].unique())
                    data.append({'Category': category, 'Max Date Status': str(match_status), 'Count': count})
    
    if not data:
        return None
    
    chart_df = pd.DataFrame(data)
    
    fig = px.bar(
        chart_df,
        x='Category',
        y='Count',
        color='Max Date Status',
        barmode='group',
        color_discrete_sequence=[COLORS['ok'], COLORS['not_ok']],
        text='Count'
    )
    
    fig.update_traces(textposition='outside', textfont_size=11)
    fig.update_layout(
        title=dict(text="Max Date Matching Status", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title="", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="Dataset Count", gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(title="Status")
    )
    return fig


def create_data_match_histogram(df_summary):
    """Create histogram for % data match distribution."""
    if df_summary is None or df_summary.empty:
        return None
    
    data_match_col = None
    for col in ['% data match', 'data_match_pct', '% Data Match']:
        if col in df_summary.columns:
            data_match_col = col
            break
    
    if data_match_col is None:
        return None
    
    # Filter out non-numeric and summary rows
    df_plot = df_summary[pd.to_numeric(df_summary[data_match_col], errors='coerce').notna()].copy()
    df_plot[data_match_col] = pd.to_numeric(df_plot[data_match_col])
    
    fig = px.histogram(
        df_plot,
        x=data_match_col,
        nbins=20,
        color_discrete_sequence=[COLORS['primary']]
    )
    
    fig.update_layout(
        title=dict(text="Distribution of % Data Match", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title="% Data Match", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="Count", gridcolor='rgba(255,255,255,0.1)')
    )
    return fig


def create_match_scatter(df_summary):
    """Create scatter plot for % date match vs % data match."""
    if df_summary is None or df_summary.empty:
        return None
    
    date_match_col = None
    data_match_col = None
    
    for col in ['% date match', 'date_match_pct', '% Date Match']:
        if col in df_summary.columns:
            date_match_col = col
            break
    
    for col in ['% data match', 'data_match_pct', '% Data Match']:
        if col in df_summary.columns:
            data_match_col = col
            break
    
    if date_match_col is None or data_match_col is None:
        return None
    
    # Filter out non-numeric rows
    df_plot = df_summary.copy()
    df_plot[date_match_col] = pd.to_numeric(df_plot[date_match_col], errors='coerce')
    df_plot[data_match_col] = pd.to_numeric(df_plot[data_match_col], errors='coerce')
    df_plot = df_plot.dropna(subset=[date_match_col, data_match_col])
    
    if df_plot.empty:
        return None
    
    fig = px.scatter(
        df_plot,
        x=date_match_col,
        y=data_match_col,
        hover_data=['Dataset ID'] if 'Dataset ID' in df_plot.columns else None,
        color_discrete_sequence=[COLORS['primary']]
    )
    
    fig.update_traces(marker=dict(size=10, opacity=0.7))
    fig.update_layout(
        title=dict(text="% Date Match vs % Data Match", font=dict(size=18, color='white')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(title="% Date Match", gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title="% Data Match", gridcolor='rgba(255,255,255,0.1)')
    )
    return fig


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    # Title with gradient
    st.markdown("""
    <h1 style="text-align: center; background: linear-gradient(90deg, #3B82F6, #8B5CF6, #EC4899); 
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
               font-size: 2.5rem; font-weight: 800; margin-bottom: 0;">
        🔍 OCL Dataset Validation Dashboard
    </h1>
    """, unsafe_allow_html=True)
    
    # Sidebar - File Upload
    with st.sidebar:
        st.markdown("### 📁 Upload Validation Files")
        st.markdown("---")
        
        ok_file = st.file_uploader(
            "✅ OK Datasets",
            type="csv",
            key="ok",
            help="Upload ok_datasets.csv"
        )
        
        partial_file = st.file_uploader(
            "⚠️ Partial OK Datasets",
            type="csv",
            key="partial",
            help="Upload partial_ok_datasets.csv"
        )
        
        not_ok_file = st.file_uploader(
            "❌ Not OK Datasets",
            type="csv",
            key="notok",
            help="Upload not_ok_datasets.csv"
        )
        
        summary_file = st.file_uploader(
            "📊 Not OK Summary",
            type="csv",
            key="summary",
            help="Upload not_ok_summary.csv"
        )
        
        st.markdown("---")
        
        # Upload status
        st.markdown("### Upload Status")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"OK: {'✅' if ok_file else '❌'}")
            st.markdown(f"Partial: {'✅' if partial_file else '❌'}")
        with col2:
            st.markdown(f"Not OK: {'✅' if not_ok_file else '❌'}")
            st.markdown(f"Summary: {'✅' if summary_file else '❌'}")
    
    # Check if files are uploaded
    if not (ok_file and partial_file and not_ok_file):
        st.markdown("""
        <div style="text-align: center; padding: 60px; background: linear-gradient(145deg, #1e293b, #334155); 
                    border-radius: 20px; margin: 40px 0;">
            <h2 style="color: #94a3b8;">👆 Upload Files to Get Started</h2>
            <p style="color: #64748b; font-size: 1.1rem;">
                Please upload at least the OK, Partial OK, and Not OK CSV files<br>
                to view the validation dashboard.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Load data
    try:
        df_ok = pd.read_csv(ok_file)
        df_partial = pd.read_csv(partial_file)
        df_not_ok = pd.read_csv(not_ok_file)
        df_summary = pd.read_csv(summary_file) if summary_file else None
    except Exception as e:
        st.error(f"Error loading files: {str(e)}")
        return
    
    # Calculate metrics
    ok_count = len(df_ok['Dataset ID'].unique()) if 'Dataset ID' in df_ok.columns else len(df_ok)
    partial_count = len(df_partial['Dataset ID'].unique()) if 'Dataset ID' in df_partial.columns else len(df_partial)
    not_ok_count = len(df_not_ok['Dataset ID'].unique()) if 'Dataset ID' in df_not_ok.columns else len(df_not_ok)
    total_count = ok_count + partial_count + not_ok_count
    success_rate = (ok_count / total_count * 100) if total_count > 0 else 0
    
    # Get sanity run date
    sanity_date = get_sanity_run_date(df_ok) or get_sanity_run_date(df_not_ok)
    
    # Display sanity run date
    st.markdown(f"""
    <p style="text-align: center; color: #94a3b8; font-size: 1rem; margin-top: -10px;">
        📅 Sanity Run Date: <strong style="color: #3B82F6;">{sanity_date}</strong>
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(create_metric_card("✅", "OK Datasets", ok_count, COLORS['ok']), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card("⚠️", "Partial OK", partial_count, COLORS['partial_ok']), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_metric_card("❌", "Not OK", not_ok_count, COLORS['not_ok']), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_metric_card("📊", "Total Datasets", total_count, COLORS['primary']), unsafe_allow_html=True)
    
    with col5:
        st.markdown(create_percentage_card("📈", "Success Rate", success_rate, COLORS['ok'] if success_rate >= 70 else COLORS['partial_ok']), unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "✅ OK Datasets", "⚠️ Partial OK", "❌ Not OK", "📈 Summary"])
    
    # ==========================================================================
    # OVERVIEW TAB
    # ==========================================================================
    with tab1:
        st.markdown("### 📊 Validation Overview")
        st.markdown("---")
        
        # Row 1: Distribution charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig_pie = create_distribution_pie(ok_count, partial_count, not_ok_count)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Combine all dataframes for case distribution
            all_cases_df = pd.concat([
                df_ok.assign(Category='OK') if not df_ok.empty else pd.DataFrame(),
                df_partial.assign(Category='Partial OK') if not df_partial.empty else pd.DataFrame(),
                df_not_ok.assign(Category='Not OK') if not df_not_ok.empty else pd.DataFrame()
            ], ignore_index=True)
            
            if not all_cases_df.empty:
                fig_cases = create_case_distribution_bar(all_cases_df)
                if fig_cases:
                    st.plotly_chart(fig_cases, use_container_width=True)
        
        # Row 2: More charts
        col1, col2 = st.columns(2)
        
        with col1:
            fig_ingest = create_ingest_type_bar(df_ok, df_partial, df_not_ok)
            if fig_ingest:
                st.plotly_chart(fig_ingest, use_container_width=True)
        
        with col2:
            fig_status = create_status_flag_pie(df_partial, df_not_ok)
            if fig_status:
                st.plotly_chart(fig_status, use_container_width=True)
        
        # Row 3: Max date chart
        col1, col2 = st.columns(2)
        with col1:
            fig_max_date = create_max_date_bar(df_partial, df_not_ok)
            if fig_max_date:
                st.plotly_chart(fig_max_date, use_container_width=True)
        
        # Export all data
        st.markdown("---")
        st.markdown("### 📥 Export Full Report")
        
        excel_data = convert_dfs_to_excel({
            'OK Datasets': df_ok,
            'Partial OK': df_partial,
            'Not OK': df_not_ok,
            'Summary': df_summary
        })
        
        st.download_button(
            label="📥 Download Full Report (Excel)",
            data=excel_data,
            file_name=f"ocl_validation_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # ==========================================================================
    # OK DATASETS TAB
    # ==========================================================================
    with tab2:
        st.markdown("### ✅ OK Datasets")
        st.markdown("---")
        
        # Filters
        with st.expander("🔍 Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_ok = st.text_input("Search Dataset ID", key="search_ok", placeholder="Enter Dataset ID...")
            
            with col2:
                status_col = 'Status' if 'Status' in df_ok.columns else None
                if status_col:
                    status_filter = st.multiselect("Status", options=df_ok[status_col].unique(), key="ok_status")
                else:
                    status_filter = []
            
            with col3:
                ingest_col = next((c for c in ['Ingestion type', 'Ingest type'] if c in df_ok.columns), None)
                if ingest_col:
                    ingest_filter = st.multiselect("Ingest Type", options=df_ok[ingest_col].unique(), key="ok_ingest")
                else:
                    ingest_filter = []
        
        # Apply filters
        filtered_ok = df_ok.copy()
        if search_ok:
            filtered_ok = search_dataset(filtered_ok, search_ok)
        if status_filter and status_col:
            filtered_ok = filtered_ok[filtered_ok[status_col].isin(status_filter)]
        if ingest_filter and ingest_col:
            filtered_ok = filtered_ok[filtered_ok[ingest_col].isin(ingest_filter)]
        
        # Display count
        st.markdown(f"**Showing {len(filtered_ok):,} records**")
        
        # Display table
        st.dataframe(filtered_ok, use_container_width=True, height=500)
        
        # Download
        st.download_button(
            label="📥 Download Filtered Results (CSV)",
            data=convert_df_to_csv(filtered_ok),
            file_name="ok_datasets_filtered.csv",
            mime="text/csv"
        )
    
    # ==========================================================================
    # PARTIAL OK DATASETS TAB
    # ==========================================================================
    with tab3:
        st.markdown("### ⚠️ Partial OK Datasets")
        st.markdown("---")
        
        # Filters
        with st.expander("🔍 Filters", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                search_partial = st.text_input("Search Dataset ID", key="search_partial", placeholder="Enter Dataset ID...")
            
            with col2:
                ingest_col = next((c for c in ['Ingest type', 'Ingestion type'] if c in df_partial.columns), None)
                if ingest_col:
                    ingest_partial = st.multiselect("Ingest Type", options=df_partial[ingest_col].unique(), key="partial_ingest")
                else:
                    ingest_partial = []
            
            with col3:
                max_date_col = next((c for c in ['Max date not matching', 'max_date_matching'] if c in df_partial.columns), None)
                if max_date_col:
                    max_date_partial = st.multiselect("Max Date Status", options=df_partial[max_date_col].unique(), key="partial_maxdate")
                else:
                    max_date_partial = []
            
            with col4:
                reason_col = next((c for c in ['Sanity reason', 'sanity reason', 'Sanity Reason'] if c in df_partial.columns), None)
                if reason_col:
                    reasons = df_partial[reason_col].dropna().unique()
                    reason_partial = st.multiselect("Sanity Reason", options=reasons, key="partial_reason")
                else:
                    reason_partial = []
        
        # Apply filters
        filtered_partial = df_partial.copy()
        if search_partial:
            filtered_partial = search_dataset(filtered_partial, search_partial)
        if ingest_partial and ingest_col:
            filtered_partial = filtered_partial[filtered_partial[ingest_col].isin(ingest_partial)]
        if max_date_partial and max_date_col:
            filtered_partial = filtered_partial[filtered_partial[max_date_col].isin(max_date_partial)]
        if reason_partial and reason_col:
            filtered_partial = filtered_partial[filtered_partial[reason_col].isin(reason_partial)]
        
        # Display count
        unique_datasets = filtered_partial['Dataset ID'].nunique() if 'Dataset ID' in filtered_partial.columns else len(filtered_partial)
        st.markdown(f"**Showing {len(filtered_partial):,} records ({unique_datasets:,} unique datasets)**")
        
        # Display table
        st.dataframe(filtered_partial, use_container_width=True, height=500)
        
        # Download
        st.download_button(
            label="📥 Download Filtered Results (CSV)",
            data=convert_df_to_csv(filtered_partial),
            file_name="partial_ok_datasets_filtered.csv",
            mime="text/csv"
        )
    
    # ==========================================================================
    # NOT OK DATASETS TAB
    # ==========================================================================
    with tab4:
        st.markdown("### ❌ Not OK Datasets")
        st.markdown("---")
        
        # Filters
        with st.expander("🔍 Filters", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                search_notok = st.text_input("Search Dataset ID", key="search_notok", placeholder="Enter Dataset ID...")
            
            with col2:
                ingest_col = next((c for c in ['Ingest type', 'Ingestion type'] if c in df_not_ok.columns), None)
                if ingest_col:
                    ingest_notok = st.multiselect("Ingest Type", options=df_not_ok[ingest_col].unique(), key="notok_ingest")
                else:
                    ingest_notok = []
            
            with col3:
                status_col = next((c for c in ['Status flag', 'status_flag'] if c in df_not_ok.columns), None)
                if status_col:
                    status_notok = st.multiselect("Status Flag", options=df_not_ok[status_col].unique(), key="notok_status")
                else:
                    status_notok = []
            
            with col4:
                reason_col = next((c for c in ['Sanity reason', 'sanity reason', 'Sanity Reason'] if c in df_not_ok.columns), None)
                if reason_col:
                    reasons = df_not_ok[reason_col].dropna().unique()
                    reason_notok = st.multiselect("Sanity Reason", options=reasons, key="notok_reason")
                else:
                    reason_notok = []
        
        # Apply filters
        filtered_notok = df_not_ok.copy()
        if search_notok:
            filtered_notok = search_dataset(filtered_notok, search_notok)
        if ingest_notok and ingest_col:
            filtered_notok = filtered_notok[filtered_notok[ingest_col].isin(ingest_notok)]
        if status_notok and status_col:
            filtered_notok = filtered_notok[filtered_notok[status_col].isin(status_notok)]
        if reason_notok and reason_col:
            filtered_notok = filtered_notok[filtered_notok[reason_col].isin(reason_notok)]
        
        # Display count
        unique_datasets = filtered_notok['Dataset ID'].nunique() if 'Dataset ID' in filtered_notok.columns else len(filtered_notok)
        st.markdown(f"**Showing {len(filtered_notok):,} records ({unique_datasets:,} unique datasets)**")
        
        # Add count difference column
        if 'old count' in filtered_notok.columns and 'new count' in filtered_notok.columns:
            filtered_notok['Count Diff'] = pd.to_numeric(filtered_notok['old count'], errors='coerce') - pd.to_numeric(filtered_notok['new count'], errors='coerce')
        
        # Display table
        st.dataframe(
            filtered_notok,
            use_container_width=True,
            height=500
        )
        
        # Download
        st.download_button(
            label="📥 Download Filtered Results (CSV)",
            data=convert_df_to_csv(filtered_notok),
            file_name="not_ok_datasets_filtered.csv",
            mime="text/csv"
        )
    
    # ==========================================================================
    # SUMMARY TAB
    # ==========================================================================
    with tab5:
        st.markdown("### 📈 Not OK Summary Analysis")
        st.markdown("---")
        
        if df_summary is None or df_summary.empty:
            st.warning("⚠️ No summary file uploaded. Please upload not_ok_summary.csv to view this section.")
        else:
            # Display summary stats
            st.markdown("#### 📊 Summary Statistics")
            
            # Filter to only data rows (not the summary row)
            numeric_cols = ['% date match', '% date unmatch', '% data match', '% data unmatch']
            available_cols = [c for c in numeric_cols if c in df_summary.columns]
            
            if available_cols:
                # Create a copy for display
                summary_display = df_summary.copy()
                
                # Convert to numeric for statistics
                for col in available_cols:
                    summary_display[col] = pd.to_numeric(summary_display[col], errors='coerce')
                
                # Show statistics
                col1, col2, col3, col4 = st.columns(4)
                
                stats_df = summary_display[available_cols].describe()
                
                for i, col in enumerate(available_cols):
                    with [col1, col2, col3, col4][i % 4]:
                        mean_val = stats_df.loc['mean', col] if col in stats_df.columns else 0
                        st.metric(col, f"{mean_val:.1f}%" if not pd.isna(mean_val) else "N/A")
            
            st.markdown("---")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                fig_hist = create_data_match_histogram(df_summary)
                if fig_hist:
                    st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                fig_scatter = create_match_scatter(df_summary)
                if fig_scatter:
                    st.plotly_chart(fig_scatter, use_container_width=True)
            
            st.markdown("---")
            
            # Full summary table
            st.markdown("#### 📋 Full Summary Table")
            
            # Filters
            col1, col2 = st.columns([1, 3])
            with col1:
                search_summary = st.text_input("Search Dataset ID", key="search_summary", placeholder="Enter Dataset ID...")
            
            filtered_summary = df_summary.copy()
            if search_summary:
                filtered_summary = search_dataset(filtered_summary, search_summary)
            
            st.dataframe(filtered_summary, use_container_width=True, height=400)
            
            # Identify worst performing datasets
            st.markdown("---")
            st.markdown("#### ⚠️ Lowest Match Datasets")
            
            data_match_col = next((c for c in ['% data match', 'data_match_pct'] if c in df_summary.columns), None)
            if data_match_col:
                df_sorted = df_summary.copy()
                df_sorted[data_match_col] = pd.to_numeric(df_sorted[data_match_col], errors='coerce')
                df_sorted = df_sorted.dropna(subset=[data_match_col])
                df_sorted = df_sorted.nsmallest(10, data_match_col)
                st.dataframe(df_sorted, use_container_width=True)
            
            # Download
            st.download_button(
                label="📥 Download Summary (CSV)",
                data=convert_df_to_csv(filtered_summary),
                file_name="not_ok_summary_filtered.csv",
                mime="text/csv"
            )


if __name__ == "__main__":
    main()

