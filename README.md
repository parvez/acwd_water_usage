# ACWD Water Usage for Home Assistant

The ACWD Water Usage is an integration for Home Assistant that enables users to monitor their water consumption data provided by the Alameda County Water District. This custom component fetches water usage details, billing information, and presents historical usage data in an easily digestible format within the Home Assistant UI.

## Features

- **Real-time Water Usage Monitoring**: Keeps track of your water usage in real-time, giving you insights into your daily consumption patterns.
- **Historical Data Visualization**: With the integration of the ApexCharts Card, users can visualize their water usage over the last 7 days, helping identify trends and potential leaks.
- **Billing Information**: Access billing details directly from your dashboard, including due dates and amounts.
- **Customizable Data Retrieval**: Fetch and combine water usage data for a configurable number of past days for detailed analysis.

## How It Works

1. **Data Collection**: The sensor connects to the ACWD portal using the provided credentials to fetch water usage data.
2. **Data Processing**: The data is processed and formatted to be compatible with Home Assistant's standards.
3. **Visualization**: Users can view their usage data through custom Lovelace cards, offering a comprehensive view of consumption over specified periods.

## Configuration

Once you have installed the ACWD Water Usage integration, you can configure it directly from the Home Assistant UI:

1. Navigate to **Settings** > **Devices & Services** in Home Assistant.
2. Click the **+ ADD INTEGRATION** button at the bottom right of the page.
3. Search for "ACWD Water Usage" in the list of integrations and select it.
4. When prompted, enter your ACWD portal credentials:
    - **Username**: Enter the username associated with your ACWD account.
    - **Password**: Enter the password for your ACWD account.
5. After entering your credentials, click **SUBMIT** to log in and retrieve your water usage data.

<img width="350" alt="ACWD Water Usage Login" src="https://github.com/parvez/acwd_water_usage/assets/126749/eb7a691b-0adb-4539-8d08-8005f39b85f2">

Please ensure that you enter the correct credentials to avoid any login issues. The integration will securely store and use these credentials to fetch your water usage data from the ACWD portal.

## Caveat

Please note that due to the data retrieval policies of the Alameda County Water District (ACWD) portal, water usage data for the last 24 hours may not be available. The integration will display the most recent data provided by the ACWD portal, which may exclude the past day's usage.

We recommend users to take this into consideration when viewing their water usage data and to plan any water usage analysis or automation accordingly.

## Setup and Configuration

### Prerequisites

- Home Assistant instance (preferably the latest version).
- Credentials for the ACWD online portal.

### Installation

1. Copy the custom component files to your Home Assistant configuration directory under `custom_components/acwd_water_usage/`.
2. Restart Home Assistant to pick up the new integration.

### Configuring the ApexCharts Card

To visualize the water usage data, set up an ApexCharts Card with the following configuration:

```yaml
type: custom:apexcharts-card
graph_span: 48h
series:
  - entity: sensor.acwd_water_usage
    type: column
    data_generator: |
      return entity.attributes.time_series.map((entry) => {
        return [new Date(entry[0]), entry[1]];
      });
```

### Usage

Once the sensor is configured and running, the water usage data can be accessed via the sensor's state and attributes. The information can be displayed using various Lovelace cards, and historical data is visualized using the ApexCharts Card.

|Yesterday|Last 7 Days|
|--|--|
|<img width="510" alt="Water_Consumption_–_Home_Assistant" src="https://github.com/parvez/acwd_water_usage/assets/126749/e2588f07-4f79-4ccf-b68d-42f42f4ad4d2">|<img width="508" alt="Water_Consumption_–_Home_Assistant-2" src="https://github.com/parvez/acwd_water_usage/assets/126749/3fc884d0-3059-46b5-8b15-c7c6080f99f7">|

### Reference Images

The provided images illustrate the UI presentation of the water consumption data as seen in Home Assistant. The first image shows a weekly overview, and the second image provides a detailed view within a 24-hour period.
