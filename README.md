# ACWD Water Usage Sensor for Home Assistant

The ACWD Water Usage Sensor is an integration for Home Assistant that enables users to monitor their water consumption data provided by the Alameda County Water District. This custom component fetches water usage details, billing information, and presents historical usage data in an easily digestible format within the Home Assistant UI.

## Features

- **Real-time Water Usage Monitoring**: Keeps track of your water usage in real-time, giving you insights into your daily consumption patterns.
- **Historical Data Visualization**: With the integration of the ApexCharts Card, users can visualize their water usage over the last 7 days, helping identify trends and potential leaks.
- **Billing Information**: Access billing details directly from your dashboard, including due dates and amounts.
- **Customizable Data Retrieval**: Fetch and combine water usage data for a configurable number of past days for detailed analysis.

## How It Works

1. **Data Collection**: The sensor connects to the ACWD portal using the provided credentials to fetch water usage data.
2. **Data Processing**: The data is processed and formatted to be compatible with Home Assistant's standards.
3. **Visualization**: Users can view their usage data through custom Lovelace cards, offering a comprehensive view of consumption over specified periods.

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
