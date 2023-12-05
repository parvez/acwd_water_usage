# acwd_water_usage
Home Assistant ACWD Water Usage

|Yesterday|Last 7 Days|
|--|--|
|<img width="510" alt="Water_Consumption_–_Home_Assistant" src="https://github.com/parvez/acwd_water_usage/assets/126749/e2588f07-4f79-4ccf-b68d-42f42f4ad4d2">|<img width="508" alt="Water_Consumption_–_Home_Assistant-2" src="https://github.com/parvez/acwd_water_usage/assets/126749/3fc884d0-3059-46b5-8b15-c7c6080f99f7">|



# Apex Chart Configuration
```
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
