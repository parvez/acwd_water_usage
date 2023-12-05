# acwd_water_usage
Home Assistant ACWD Water Usage

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