"""
Wallet monitoring page for ApexWatch Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from config import settings
from page_modules.utils import make_api_request
from database import get_db_connection


@st.cache_data(ttl=300)
def get_transaction_trends(token_id: str, days: int = 7):
    """Get transaction trends over time"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            DATE_TRUNC('hour', timestamp) as hour,
            COUNT(*) as tx_count,
            SUM(amount) as total_volume,
            AVG(amount) as avg_amount
        FROM wallet_transactions
        WHERE token_id = %s
            AND timestamp > NOW() - INTERVAL '%s days'
        GROUP BY hour
        ORDER BY hour DESC
        """

        cur.execute(query, (token_id, days))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['hour', 'tx_count', 'total_volume', 'avg_amount'])
            df['hour'] = pd.to_datetime(df['hour'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching transaction trends: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_whale_activity_heatmap(token_id: str):
    """Get whale activity by day of week and hour"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            EXTRACT(DOW FROM wt.timestamp) as day_of_week,
            EXTRACT(HOUR FROM wt.timestamp) as hour_of_day,
            COUNT(*) as activity_count
        FROM wallet_transactions wt
        JOIN watched_wallets ww ON ww.address IN (wt.from_address, wt.to_address)
            AND ww.token_id = wt.token_id
        WHERE wt.token_id = %s
            AND ww.is_whale = TRUE
            AND wt.timestamp > NOW() - INTERVAL '30 days'
        GROUP BY day_of_week, hour_of_day
        ORDER BY day_of_week, hour_of_day
        """

        cur.execute(query, (token_id,))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['day_of_week', 'hour_of_day', 'activity_count'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching whale activity heatmap: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_top_transaction_pairs(token_id: str, limit: int = 10):
    """Get most frequent transaction pairs"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
        SELECT
            from_address,
            to_address,
            COUNT(*) as tx_count,
            SUM(amount) as total_amount,
            MAX(timestamp) as last_tx
        FROM wallet_transactions
        WHERE token_id = %s
            AND timestamp > NOW() - INTERVAL '30 days'
        GROUP BY from_address, to_address
        ORDER BY tx_count DESC
        LIMIT %s
        """

        cur.execute(query, (token_id, limit))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['from_address', 'to_address', 'tx_count', 'total_amount', 'last_tx'])
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching transaction pairs: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_wallet_balance_history(token_id: str, address: str, days: int = 30):
    """Calculate wallet balance over time (approximate)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get all transactions for this wallet
        query = """
        SELECT
            timestamp,
            CASE
                WHEN from_address = %s THEN -amount
                ELSE amount
            END as net_change
        FROM wallet_transactions
        WHERE token_id = %s
            AND (from_address = %s OR to_address = %s)
            AND timestamp > NOW() - INTERVAL '%s days'
        ORDER BY timestamp ASC
        """

        cur.execute(query, (address, token_id, address, address, days))
        results = cur.fetchall()

        cur.close()
        conn.close()

        if results:
            df = pd.DataFrame(results, columns=['timestamp', 'net_change'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['cumulative_change'] = df['net_change'].cumsum()
            return df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Error fetching balance history: {e}")
        return pd.DataFrame()


def wallets_page():
    """Display wallet monitoring page"""
    st.title("👛 Wallet Monitoring")

    if not st.session_state.selected_token:
        st.warning("Please select a token from the Overview page")
        return

    token_id = st.session_state.selected_token

    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # Get wallet summary
    wallet_data = make_api_request(
        f"{settings.WALLET_MONITOR_URL}/api/wallets/summary/{token_id}"
    )

    if wallet_data and wallet_data.get('wallets'):
        wallets_df = pd.DataFrame(wallet_data['wallets'])

        # Wallet statistics
        st.markdown("### 📊 Wallet Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_wallets = len(wallets_df)
            st.metric("Total Wallets", total_wallets)
        with col2:
            whale_count = wallets_df['is_whale'].sum() if 'is_whale' in wallets_df.columns else 0
            st.metric("Whale Wallets", whale_count)
        with col3:
            auto_discovered = wallets_df['discovered_automatically'].sum() if 'discovered_automatically' in wallets_df.columns else 0
            st.metric("Auto-Discovered", auto_discovered)
        with col4:
            total_balance = wallets_df['balance'].sum() if 'balance' in wallets_df.columns else 0
            st.metric("Total Balance", f"{total_balance:,.2f}")

        st.markdown("---")

        # Whale wallet distribution
        st.markdown("### 🐋 Whale Wallet Distribution")

        if 'is_whale' in wallets_df.columns and 'balance' in wallets_df.columns:
            col1, col2 = st.columns(2)

            with col1:
                # Whale vs non-whale pie chart
                whale_dist = wallets_df.groupby('is_whale').size().reset_index(name='count')
                whale_dist['type'] = whale_dist['is_whale'].map({True: 'Whale', False: 'Regular'})

                fig = px.pie(
                    whale_dist,
                    values='count',
                    names='type',
                    title='Wallet Type Distribution',
                    hole=0.4,
                    color_discrete_map={'Whale': '#FF6B6B', 'Regular': '#4ECDC4'}
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Balance distribution
                whale_balance = wallets_df.groupby('is_whale')['balance'].sum().reset_index()
                whale_balance['type'] = whale_balance['is_whale'].map({True: 'Whale', False: 'Regular'})

                fig = px.bar(
                    whale_balance,
                    x='type',
                    y='balance',
                    title='Balance by Wallet Type',
                    labels={'balance': 'Total Balance', 'type': 'Wallet Type'},
                    color='type',
                    color_discrete_map={'Whale': '#FF6B6B', 'Regular': '#4ECDC4'}
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        st.markdown("### 🐋 Top Whale Wallets")

        # Display top wallets
        display_columns = ['address', 'balance', 'is_whale', 'discovered_automatically', 'last_activity']
        available_columns = [col for col in display_columns if col in wallets_df.columns]

        if available_columns:
            # Make addresses clickable and sortable
            display_df = wallets_df[available_columns].copy()

            # Format balance
            if 'balance' in display_df.columns:
                display_df = display_df.sort_values('balance', ascending=False)

            st.dataframe(
                display_df.head(20),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")

        # Transaction Trends
        st.markdown("### 📈 Transaction Trends")

        col1, col2 = st.columns([3, 1])
        with col2:
            trend_days = st.selectbox("Time Period", [7, 14, 30], format_func=lambda x: f"{x} days", key="trend_days")

        tx_trends = get_transaction_trends(token_id, trend_days)

        if not tx_trends.empty:
            # Transaction count over time
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=tx_trends['hour'],
                y=tx_trends['tx_count'],
                name='Transaction Count',
                marker_color='#5F27CD'
            ))

            fig.update_layout(
                title=f'Transaction Frequency (Last {trend_days} days)',
                xaxis_title='Time',
                yaxis_title='Transaction Count',
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Volume over time
            fig = px.area(
                tx_trends,
                x='hour',
                y='total_volume',
                title=f'Transaction Volume (Last {trend_days} days)',
                labels={'total_volume': 'Total Volume', 'hour': 'Time'}
            )

            fig.update_traces(fill='tozeroy', line_color='#00D2D3')
            st.plotly_chart(fig, use_container_width=True)

            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                total_tx = tx_trends['tx_count'].sum()
                st.metric("Total Transactions", f"{int(total_tx):,}")
            with col2:
                total_vol = tx_trends['total_volume'].sum()
                st.metric("Total Volume", f"{total_vol:,.2f}")
            with col3:
                avg_tx_size = tx_trends['avg_amount'].mean()
                st.metric("Avg Transaction Size", f"{avg_tx_size:,.2f}")
        else:
            st.info("No transaction trend data available")

        st.markdown("---")

        # Whale Activity Heatmap
        st.markdown("### 🔥 Whale Activity Heatmap")

        heatmap_data = get_whale_activity_heatmap(token_id)

        if not heatmap_data.empty:
            # Create pivot table for heatmap
            heatmap_pivot = heatmap_data.pivot(
                index='hour_of_day',
                columns='day_of_week',
                values='activity_count'
            ).fillna(0)

            # Map day numbers to names
            day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
            heatmap_pivot.columns = [day_names[int(col)] if col < len(day_names) else str(col) for col in heatmap_pivot.columns]

            fig = go.Figure(data=go.Heatmap(
                z=heatmap_pivot.values,
                x=heatmap_pivot.columns,
                y=heatmap_pivot.index,
                colorscale='YlOrRd',
                hovertemplate='Day: %{x}<br>Hour: %{y}<br>Activity: %{z}<extra></extra>'
            ))

            fig.update_layout(
                title='Whale Activity by Day & Hour (Last 30 days)',
                xaxis_title='Day of Week',
                yaxis_title='Hour of Day',
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No whale activity data available for heatmap")

        st.markdown("---")

        # Top Transaction Pairs
        st.markdown("### 🔀 Top Transaction Pairs")

        tx_pairs = get_top_transaction_pairs(token_id, 15)

        if not tx_pairs.empty:
            # Shorten addresses for display
            tx_pairs['from_short'] = tx_pairs['from_address'].str[:6] + '...' + tx_pairs['from_address'].str[-4:]
            tx_pairs['to_short'] = tx_pairs['to_address'].str[:6] + '...' + tx_pairs['to_address'].str[-4:]
            tx_pairs['pair'] = tx_pairs['from_short'] + ' → ' + tx_pairs['to_short']

            fig = px.bar(
                tx_pairs.head(10),
                x='tx_count',
                y='pair',
                orientation='h',
                title='Most Frequent Transaction Routes',
                labels={'tx_count': 'Transaction Count', 'pair': 'From → To'},
                hover_data=['total_amount', 'last_tx']
            )

            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

            # Display full table
            with st.expander("📋 View Full Transaction Pairs Table"):
                st.dataframe(
                    tx_pairs[['from_address', 'to_address', 'tx_count', 'total_amount', 'last_tx']],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No transaction pair data available")

        st.markdown("---")

        # Wallet Detail Analyzer
        st.markdown("### 🔍 Wallet Detail Analyzer")

        st.write("Select a wallet to view detailed balance history:")

        wallet_addresses = wallets_df['address'].tolist() if 'address' in wallets_df.columns else []

        if wallet_addresses:
            selected_wallet = st.selectbox(
                "Select Wallet",
                wallet_addresses,
                format_func=lambda x: f"{x[:10]}...{x[-8:]}" if len(x) > 20 else x,
                key="wallet_selector"
            )

            if selected_wallet:
                col1, col2 = st.columns([3, 1])
                with col2:
                    balance_days = st.selectbox("History Period", [7, 14, 30, 60], format_func=lambda x: f"{x} days", key="balance_days")

                balance_history = get_wallet_balance_history(token_id, selected_wallet, balance_days)

                if not balance_history.empty:
                    fig = px.line(
                        balance_history,
                        x='timestamp',
                        y='cumulative_change',
                        title=f'Balance Change History: {selected_wallet[:10]}...{selected_wallet[-8:]}',
                        labels={'cumulative_change': 'Cumulative Change', 'timestamp': 'Time'}
                    )

                    fig.update_traces(line_color='#1DD1A1', line_width=3)
                    fig.update_layout(hovermode='x unified')

                    st.plotly_chart(fig, use_container_width=True)

                    # Balance change stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_received = balance_history[balance_history['net_change'] > 0]['net_change'].sum()
                        st.metric("Total Received", f"{total_received:,.2f}")
                    with col2:
                        total_sent = abs(balance_history[balance_history['net_change'] < 0]['net_change'].sum())
                        st.metric("Total Sent", f"{total_sent:,.2f}")
                    with col3:
                        net_change = balance_history['net_change'].sum()
                        st.metric("Net Change", f"{net_change:,.2f}", delta=f"{net_change:,.2f}")
                else:
                    st.info(f"No transaction history for wallet {selected_wallet[:10]}... in the selected period")

        st.markdown("---")
        st.markdown("### 📊 Recent Transactions")

        # Get recent transactions
        tx_data = make_api_request(
            f"{settings.WALLET_MONITOR_URL}/api/transactions/{token_id}?limit=50"
        )

        if tx_data and tx_data.get('transactions'):
            tx_df = pd.DataFrame(tx_data['transactions'])

            # Format for display
            display_tx = tx_df[['timestamp', 'from', 'to', 'amount', 'tx_hash']].copy()
            display_tx['from'] = display_tx['from'].str[:10] + '...'
            display_tx['to'] = display_tx['to'].str[:10] + '...'
            display_tx['tx_hash'] = display_tx['tx_hash'].str[:16] + '...'

            st.dataframe(
                display_tx,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recent transactions")
    else:
        st.info("No wallets being monitored")
