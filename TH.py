import streamlit as st
import pandas as pd
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
import os

# Ruta local del archivo CSV
file_path = 'Joacofurlan/claroth/Datos_reporteFB.csv'

@st.cache_data
def cargar_datos(file_path):
    # Leer el CSV especificando la codificación y el separador
    df = pd.read_csv(file_path, encoding='utf-8', sep=';')
    # Convertir las columnas THP a numéricas si es posible
    df['THP Claro'] = pd.to_numeric(df['THP Claro'].str.replace(',', '.'), errors='coerce')
    df['THP Personal'] = pd.to_numeric(df['THP Personal'].str.replace(',', '.'), errors='coerce')
    df['THP Movistar'] = pd.to_numeric(df['THP Movistar'].str.replace(',', '.'), errors='coerce')
    
    # Eliminar las comas de las columnas de muestras y convertir a numérico
    df['Muestras Claro'] = pd.to_numeric(df['Muestras Claro'].str.replace(',', ''), errors='coerce')
    df['Muestras Personal'] = pd.to_numeric(df['Muestras Personal'].str.replace(',', ''), errors='coerce')
    df['Muestras Movistar'] = pd.to_numeric(df['Muestras Movistar'].str.replace(',', ''), errors='coerce')

    return df

try:
    # Cargar los datos
    df = cargar_datos(file_path)

    # Definir el orden de los meses
    meses_ordenados = ['ene-24', 'feb-24', 'mar-24', 'abr-24', 'may-24', 'jun-24']
    
    # Calcular promedios THP para cada periodo y operador
    promedios = df.groupby('Periodo')[['THP Claro', 'THP Personal', 'THP Movistar']].mean().reset_index()

    # Asegurar que el periodo esté en el orden correcto 
    promedios['Periodo'] = pd.Categorical(promedios['Periodo'], categories=meses_ordenados, ordered=True)
    promedios = promedios.sort_values('Periodo')

    # Verificar si hay datos antes de continuar
    if promedios.empty:
        st.warning("No hay datos disponibles para los períodos seleccionados.")
    else:
        # Columnas de THP   
        thp_columns = ['THP Claro', 'THP Personal', 'THP Movistar']   

        # Crear un filtro para seleccionar el mes
        mes_seleccionado = st.selectbox("Seleccionar Mes", meses_ordenados)

        # Función para obtener el valor del THP y la variación respecto al mes anterior
        def obtener_valores(promedios, mes, columna):
            valor_mes = promedios.loc[promedios['Periodo'] == mes, columna].values[0]
            mes_anterior = meses_ordenados[meses_ordenados.index(mes) - 1] if meses_ordenados.index(mes) > 0 else None
            if mes_anterior:
                valor_anterior = promedios.loc[promedios['Periodo'] == mes_anterior, columna].values[0]
                variacion = (valor_mes - valor_anterior) / valor_anterior * 100
            else:
                variacion = None
            return valor_mes, variacion

        # Mostrar las métricas en columnas
        cols = st.columns(3)
        for i, metrica in enumerate(thp_columns):
            with cols[i]:
                st.subheader(metrica)
                valor_mes, variacion = obtener_valores(promedios, mes_seleccionado, metrica)
                if variacion is not None:
                    st.metric(label="", value=f'{valor_mes:.2f} GB', delta=f'{variacion:.2f}%')
                else:
                    st.metric(label="", value=f'{valor_mes:.2f} GB')

        # Crear un gráfico de líneas mejorado con colores específicos
        st.header("GRAFICOS THROUGHPUT", divider='rainbow')
        st.markdown("## **<span style='color:darkred;'>THP Operador</span>**", unsafe_allow_html=True)
        fig = px.line(
            promedios,
            x='Periodo',
            y=thp_columns,
            labels={'value': 'THP (GB)', 'Periodo': 'Periodo'},
            markers=True
        )
        
        # Asignar colores específicos a cada línea
        color_map = {
            'THP Claro': 'red',
            'THP Personal': 'blue',
            'THP Movistar': 'lightblue'
        }
        for operador, color in color_map.items():
            fig.update_traces(line=dict(color=color), selector=dict(name=operador))

        # Personalizar el gráfico
        fig.update_layout(
            xaxis_title='',
            yaxis_title='THP (GB)',
            legend_title='Operadores',
        )

        # Mostrar el gráfico en Streamlit
        st.plotly_chart(fig)

    # Widget de selección única para la Provincia
    provincia_seleccionada = st.sidebar.selectbox("Provincia", df["Provincia"].unique())

    # Filtrar por Provincia seleccionada
    df_filtered = df[df["Provincia"] == provincia_seleccionada]

    # Widget de selección múltiple para la localidad
    localidad_seleccionada = st.sidebar.multiselect("Localidad", df_filtered["Localidad"].unique())

    # Filtrar por localidad seleccionada
    if not localidad_seleccionada:
        df_filtered_localidades = df_filtered.copy()
    else:
        df_filtered_localidades = df_filtered[df_filtered["Localidad"].isin(localidad_seleccionada)]

    # Convertir la columna Periodo a categoría con el orden deseado
    df_filtered['Periodo'] = pd.Categorical(df_filtered['Periodo'], categories=meses_ordenados, ordered=True)
    df_filtered_localidades['Periodo'] = pd.Categorical(df_filtered_localidades['Periodo'], categories=meses_ordenados, ordered=True)

    if not df_filtered.empty:
        # Gráfico de líneas por provincia (THP Claro)
        df_grouped_line_provincias_claro = df_filtered.groupby(['Periodo', 'Provincia'])['THP Claro'].mean().reset_index()

        fig_line_provincias_claro = px.line(df_grouped_line_provincias_claro, x='Periodo', y='THP Claro', color='Provincia',
                                            line_group='Provincia', markers=True, 
                                            labels={'THP Claro': 'THP (GB)'},
                                            title='Provincia')

        # Configurar el gráfico de líneas para mostrar los valores al pasar el mouse
        fig_line_provincias_claro.update_traces(mode='lines+markers', hovertemplate='%{y}')
        fig_line_provincias_claro.update_layout(hovermode='closest', yaxis=dict(range=[0, df_grouped_line_provincias_claro['THP Claro'].max() * 2]))

        # Asignar color específico
        fig_line_provincias_claro.update_traces(line=dict(color='red'))

    # Gráfico de líneas por localidad solo si hay selección de localidades (THP Claro)
    if localidad_seleccionada and not df_filtered_localidades.empty:
        df_grouped_line_localidades = df_filtered_localidades.groupby(['Periodo', 'Provincia', 'Localidad'])['THP Claro'].mean().reset_index()

        fig_line_localidades = px.line(df_grouped_line_localidades, x='Periodo', y='THP Claro', color='Localidad',
                                       markers=True, labels={'THP Claro': 'THP (GB)'},
                                       title='Localidad')

        # Configurar el gráfico de líneas para mostrar los valores al pasar el mouse
        fig_line_localidades.update_traces(mode='lines+markers', hovertemplate='%{y}')
        fig_line_localidades.update_layout(hovermode='closest')

    # Gráfico de líneas comparativo (THP Claro, THP Personal, THP Movistar)
    df_grouped_comparison = df_filtered.groupby(['Periodo', 'Provincia'])[['THP Claro', 'THP Personal', 'THP Movistar']].mean().reset_index()
    st.markdown("## **<span style='color:darkred;'>THP Operador Provincia</span>**", unsafe_allow_html=True)
    # Convertir a formato largo para Plotly Express
    df_melted = df_grouped_comparison.melt(id_vars=['Periodo', 'Provincia'], 
                                           value_vars=['THP Claro', 'THP Personal', 'THP Movistar'],
                                           var_name='Operador', value_name='THP')

    fig_comparison = px.line(df_melted, x='Periodo', y='THP', color='Operador', line_group='Provincia', 
                             markers=True, 
                             labels={'THP': 'Promedio THP', 'Operador': 'Operador'},
                             )

    # Configurar el gráfico de líneas comparativo para mostrar los valores al pasar el mouse
    fig_comparison.update_traces(mode='lines+markers', hovertemplate='%{y}')
    fig_comparison.update_layout(hovermode='closest')

    # Asignar colores específicos a cada línea
    for operador, color in color_map.items():
        fig_comparison.update_traces(line=dict(color=color), selector=dict(name=operador))

    # Personalizar el gráfico comparativo
    fig_comparison.update_layout(
        xaxis_title='',
        yaxis_title='THP (GB)',
        legend_title='Operadores',
    )

    # Mostrar el gráfico de líneas comparativo en Streamlit
    st.plotly_chart(fig_comparison)
    st.markdown("## **<span style='color:darkred;'>THP Claro</span>**", unsafe_allow_html=True)
    # Mostrar los gráficos uno al lado del otro
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_line_provincias_claro)
    with col2:
        if localidad_seleccionada and not df_filtered_localidades.empty:
            st.plotly_chart(fig_line_localidades)

    # Filtrar las columnas deseadas (para mostrar en el checkbox)
    df_filtered_table = df[['Periodo', 'Provincia', 'Localidad', 'THP Claro', 'Muestras Claro', 'THP Personal', 'Muestras Personal', 'THP Movistar', 'Muestras Movistar']]

    # Configurar opciones de la tabla AgGrid
    gb = GridOptionsBuilder.from_dataframe(df_filtered_table)
    gb.configure_pagination(paginationAutoPageSize=True)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum')
    gb.configure_selection('multiple', use_checkbox=True)
    gb.configure_side_bar()
    gb.configure_grid_options(domLayout='normal')
    gb.configure_grid_options(suppressRowVirtualisation=True)
    grid_options = gb.build()
    grid_options['theme'] = 'ag-theme-fresh'

    # Mostrar tabla interactiva AgGrid
    st.markdown("## **<span style='color:darkred;'>TABLERO</span>**", unsafe_allow_html=True)
    AgGrid(df_filtered_table, gridOptions=grid_options, enable_enterprise_modules=True, height=500, fit_columns_on_grid_load=True)

    # Descargar los datos como CSV solo de los datos filtrados
    csv_filtered = df_filtered_table.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
    st.download_button(
        label="Descargar",
        data=csv_filtered,
        file_name='datos_thp_filtrados.csv',
        mime='text/csv',
    )

except Exception as e:
    st.error(f"Error al cargar o procesar los datos: {e}")
