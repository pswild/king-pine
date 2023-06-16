A package for analyzing the marginal emission impact of the proposed King Pine wind farm on the ISO-NE grid. The final report is included in this repository as a PDF for reference.

# Executive Summary

The goal of this project is to estimate how the King Pine wind farm would impact the marginal CO2 emissions rate (MER) of ISO-NE’s system using publicly available data. These findings are intended to serve as a shared baseline so that voters and policymakers can easily evaluate different policy options and make informed decisions about the future of Maine's electricity system. 

This paper is a simplified version of a resource integration study, which typically characterize how capacity additions will impact grid operations by looking at the project’s location with respect to the transmission and distribution (T&D) system and its expected generation profile. Whereas studies conducted by grid operators like ISO-NE employ production cost models to simulate how generators are dispatched in real-time as well as capacity expansion models to account for changes to the T&D system moving forward, this paper only looks at the short-term impact of a new wind capacity based on historical grid performance and the project’s forecasted output. In other words, how the ISO-NE system will change in the long run is beyond the scope of this paper. 

The basic methodology is as follows: 1) simulate the hourly generation of the King Pine wind farm, 2) identify the marginal unit type and associated CO2 emissions rate based on historical dispatch data from ISO-NE, 3) calculate how much wind generation is dispatched based on the locational marginal price (LMP) at the closest pricing node, 4) compare the marginal CO2 emissions rate (MER) of the ISO-NE system before and after the addition of new wind generation. Note that without access to a unit-level dispatch stack at each pricing node, several simplifying assumptions must be made. 

Based on the specifications outlined in the developer's term sheet, the annual energy generation of King Pine wind farm is modeled at 3,984,822 MWh. Applying the industry-standard 90% probability of exceedance yields an annual total of 3,341,590 MWh, which is roughly 4% of ISO-NE's aggregate demand. The percentage change in MER is estimated to be -0.47%, or a decline from 799 lbs CO2/MWh to 795 lbs CO2/MWh. For context, a 2019 ISO-NE economic study on the integration of offshore wind in southern New England found that increasing installed capacity from 0 MW to 1,000 MW stood to decrease the MER by roughly 1%.

# Developer Notes

- Uses 'nrel' conda environment: ``conda activate nrel``
