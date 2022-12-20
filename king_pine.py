# -*- coding: utf-8 -*-
#!/usr/bin/env python3

"""
Calculate wind generation from proposed King Pine wind farm in Northeastern Maine.

Created on Mon Dec 12 21:56:51 2022

@author: pswild
"""

import os
import json
import requests
import numpy as np
import pandas as pd

# Silence warnings...
pd.options.mode.chained_assignment = None

# API keys. 
NREL_API_KEY = 'yqjUGnkgdH4m8XrGh6OXi8rK7JMLJh6q3PafSMls'
EIA_API_KEY = 'GbKYer2Pz9JS0UttTjwxahbfN5ZzDKE0ZuyjsJQY'

# Coordinates of King Pine wind farm.
lat = 46.918
lon = -68.169

# Location ID of Maine load zone (load-weighted average of all pricing nodes in zone).
location_id = 4001 

# Nameplate capacity (MW). 
nameplate_cap = 1000

#--- PATH ---# 

# Get path.
here = os.path.dirname(os.path.realpath(__file__))

#--- DATA ---#

# Resource data and SAM configuration file.
res_file = os.path.join(here, 'tests/data/wtk/ri_100_wtk_2013.h5')
sam_file = os.path.join(here, 'tests/data/SAM/wind_gen_standard_losses_0.json')

# SAM generation data and VER wind speed data files. 
sam_gen_file = os.path.join(here, 'data/king_pine_sam_generation.csv')
ver_ws_file = os.path.join(here, 'data/onsw_windspeeds_me.csv')

# EIA generation data by fuel type file.
eia_gen_file = os.path.join(here, 'data/eia_gen_2021.csv')

# ISO-NE dispatch fuel mix file. 
iso_gen_file = os.path.join(here, 'data/iso_genfuelmix_2021.csv')

# ISO-NE locational marginal price file. 
lmp_file = os.path.join(here, 'data/lmps_2021.csv')

#--- OUTPUT ---# 

# ISO-NE generated emissions profile. 
grid_gen_file = os.path.join(here, 'output/grid_generation_profile.csv')

# King Pine avoided emissions profile. 
wind_gen_file = os.path.join(here, 'output/wind_generation_profile.csv')

def wtk():
     '''Get Wind Toolkit data.'''

     # TODO: implement using NREL-rex.

     # WKT for location.
     point = f'POINT({lon} {lat})'

     # Request URL. 
     # url_csv = f'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-download?api_key={NREL_API_KEY}&wtk={point}&names=2014&interval=60&utc=false&leap_day=false&email=parkerwild96@gmail.com'
     url_sam = f'https://developer.nrel.gov/api/wind-toolkit/v2/wind/wtk-srw-download?api_key={NREL_API_KEY}&lat={lat}&lon={lon}&hubheight=120&year=2014&utc=false&email=parkerwild96@gmail.com'

     # Method #1: Get WIND Toolkit data in CSV format.
     # response = requests.get(url_csv)

     # Method #2: Get WIND Toolkit data in SAM format.
     response = requests.get(url_sam)

     # Write response to file. 
     with open('data/wtk.csv', 'w') as f:
          f.write(response.text)

     return

def ver(): 
     '''Calculate generation profile for King Pine wind farm from VER wind speed data.'''

     # Read ISO New England wind speed data.
     ws = pd.read_csv(ver_ws_file)

     # Convert date column from string to datetime.
     ws['Date'] = pd.to_datetime(ws['Date']) + pd.to_timedelta(ws['Hour_Ending'] - 1, unit='h')

     # Extract Maine North II wind speed data.
     ws = ws[['Date', 'MaineNorth2_wnd_spd']]

     # Rename columns. 
     ws.rename({'MaineNorth2_wnd_spd': 'Wind speed (m/s)'}, axis='columns', inplace=True)

     # Set start and end dates.
     start_date = pd.to_datetime('2000-01-01 00:00:00')
     end_date = pd.to_datetime('2019-12-31 23:00:00')

     # Only look at 20 years of data.
     ws = ws[(ws['Date'] >= start_date) & (ws['Date'] <= end_date)]

     # Exclude leap days.
     ws = ws[ws['Date'].dt.strftime('%m-%d') != '02-29']

     # Remove years from date.
     ws['Date'] = ws['Date'].dt.strftime('%m-%d %H:%M')

     # Take average across 20 years.
     ws = ws.groupby('Date').mean()

     # TODO: calculate generation profile from wind speed using turbine power curve. 
     gen = None

     return gen

def sam(): 
     '''Load SAM generation profile for King Pine wind farm.'''

     # Read SAM generation data.
     gen = pd.read_csv(sam_gen_file)

     # Convert date column from string to datetime. 
     gen['Date'] = pd.to_datetime(gen['Time stamp'], format='%b %d, %I:%M %p').dt.strftime('%m-%d %H:%M')

     # Convert generation to MW.
     gen['Generation (MWh)'] = gen['System power generated | (kW)'] / 1000

     # Reformat dataframe.
     gen = gen[['Date', 'Generation (MWh)']]

     return gen

def eia():
     '''Get hourly generation by source from EIA for 2021.'''

     # Year of data.
     year = pd.DataFrame() 

     # Counter.
     i = 0

     while i < 365: 

          # Update offset. 
          offset = i * 192

          # Request URL. 
          url = f'https://api.eia.gov/v2/electricity/rto/fuel-type-data/data?api_key={EIA_API_KEY}&frequency=local-hourly&data[0]=value&facets[respondent][]=ISNE&start=2020-31-01T23:00:00-05:00&end=2022-01-01T00:00:00-05:00&sort[0][column]=period&sort[0][direction]=asc&offset={offset}&length=192'

          # Issue request. 
          response = requests.get(url)

          if response: 

               # Parse JSON as Python dictionary. 
               dict = json.loads(response.text)

               # Flatten JSON. 
               day = pd.json_normalize(dict['response']['data'])

               # Append day to year. 
               year = pd.concat([year, day], ignore_index=True)

               print('Loaded day ', i + 1)

               # Increment counter.
               i += 1

          else: 

               print('Response null. Repeating request for day ', i + 1)

     # Write dataframe to CSV.
     year.to_csv(eia_gen_file, index=False)

     return year

def iso():
     '''Get hourly generator fuel mix data from ISO-NE for 2021.'''

     # Directory path. 
     dir = 'data/genfuelmix_2021'

     # Year of data. 
     year = pd.DataFrame()

     # Combine dispatch fuel mix data.
     for file in os.listdir(dir):

          # Update path.
          path = os.path.join(dir, file)

          # Read day into dataframe. 
          day = pd.read_csv(path, skiprows=[0,1,2,3,5], index_col=False)

          # Strip extraneous information.
          day.drop(columns=['H'], inplace=True)

          # Append day to year. 
          year = pd.concat([year, day], ignore_index=True)
     
     # Combine to datetime. 
     year['Date'] = pd.to_datetime(year['Date'] + ' ' + year['Time'])

     # Sort by date.
     year.sort_values(by=['Date'], inplace=True, ignore_index=True)
     
     # Floor date to hour.
     year['Date'] = year['Date'].dt.floor(freq='H')
     
     # Format date. 
     year['Date'] = year['Date'].dt.strftime('%m-%d %H:%M')

     # Drop unused columns.
     year = year[['Date', 'Fuel Category', 'Gen Mw', 'Marginal Flag']]

     # Drop NaNs.
     year.dropna(inplace=True)

     # Aggregate by fuel type for each hour. 
     # NOTE: this simply takes the average of generation by fuel type across reporting intervals.
     # NOTE: this simply treats whichever resource was marginal first as that which was marginal throughout the hour.
     year = year.groupby(['Date', 'Fuel Category'], as_index=False).agg({'Gen Mw': 'mean', 'Marginal Flag': 'first'})

     # Rename columns. 
     year.rename({'Gen Mw': 'Generation (MWh)'}, axis='columns', inplace=True)

     # Write dataframe to CSV.
     year.to_csv(iso_gen_file, index=False)

     return year

def lmp(location_id):
     '''Get hourly real-time locational marginal prices for ISO-NE pricing node with location_id in 2021.'''

     # Directory path. 
     dir = 'data/lmps_2021'

     # Year of data. 
     year = pd.DataFrame()

     # Combine locational marginal price data.
     for file in os.listdir(dir):

          # Update path.
          path = os.path.join(dir, file)

          # Read day into dataframe. 
          day = pd.read_csv(path, skiprows=[0,1,2,3,5], index_col=False)

          # Strip extraneous information.
          day.drop(columns=['H'], inplace=True)

          # Select subset of LMPs for one location. 
          day = day.loc[day['Location ID'] == location_id]

          # Convert hours to numeric type. 
          day['Hour Ending'] = pd.to_numeric(day['Hour Ending'])

          # Append day to year. 
          year = pd.concat([year, day], ignore_index=True)

     # Combine to datetime. 
     year['Date'] = pd.to_datetime(year['Date']) + pd.to_timedelta(year['Hour Ending'] - 1, unit='h')

     # Format date. 
     year['Date'] = year['Date'].dt.strftime('%m-%d %H:%M')

     # Sort by date.
     year.sort_values(by=['Date'], inplace=True, ignore_index=True)
          
     # Drop unused columns.
     year = year[['Date', 'Location ID', 'Location Name', 'Locational Marginal Price']]

     # Drop NaNs.
     year.dropna(inplace=True)

     # Write dataframe to CSV.
     year.to_csv(lmp_file, index=False)

     return year

def emissions(grid_gens, wind_gens, lmps):
     '''Calculates the emissions impact of the King Pine wind farm.'''

     # Dictionary of CO2 emissions rates (lbs CO2/MWh) from EPA eGRID's NPCC New England subregion in 2020. 
     co2_emissions_rates = {
          'Oil': 3374.668,
          'Coal': 2277.021,
          'Natural Gas': 850.537,
          'Refuse': 0.0, # biomass is part of carbon cycle
          'Wood': 0.0, # biomass is part of carbon cycle
          'Landfill Gas': 0.0, # flared otherwise
          'Nuclear': 0.0,
          'Hydro': 0.0,
          'Solar': 0.0,
          'Wind': 0.0,
          'Other': 0.0 # energy storage and demand response
     }

     # Threshold price ($/MWh) for onshore wind from 2019 NESCOE economic study.
     threshold_price = 4

     # Map CO2 emissions rates by fuel type.
     grid_gens['Emissions Rate (lbs CO2/MWh)'] = grid_gens['Fuel Category'].map(co2_emissions_rates)

     # Add column for marginal CO2 emissions rate (before and after). 
     wind_gens['Marginal Emissions Rate (lbs CO2/MWh) - Before'] = None
     wind_gens['Marginal Emissions Rate (lbs CO2/MWh) - After'] = None

     # Add column for curtailment flag. 
     wind_gens['Curtailed'] = False

     for hour in grid_gens['Date'].unique():

          #--- WIND GENERATION ---#

          # Get new generation for hour. 
          wind_gen = wind_gens.loc[wind_gens['Date'] == hour]['Generation (MWh)'].iloc[0]

          # --- MARGINAL GENERATOR --- #

          # Pull marginal rows in hour from grid generation data. 
          margin = grid_gens.loc[(grid_gens['Date'] == hour) & (grid_gens['Marginal Flag'] == 'Yes')]

          if margin.empty:

               # NOTE: If no marginal fuel type indicated, default to natural gas. 
               margin = grid_gens.loc[(grid_gens['Date'] == hour) & (grid_gens['Fuel Category'] == 'Natural Gas')]

               # Update marginal flag in copy and original.
               margin.loc[(margin['Date'] == hour) & (margin['Fuel Category'] == 'Natural Gas'), 'Marginal Flag'] = 'Yes'
               grid_gens.loc[(grid_gens['Date'] == hour) & (grid_gens['Fuel Category'] == 'Natural Gas'), 'Marginal Flag'] = 'Yes'

          # Get marginal grid generation.
          marginal_grid_gen = margin['Generation (MWh)'].sum()

          # Calculate load-weighted marginal C02 emissions rate (before).
          marginal_emissions_rate_before = margin.groupby('Date').apply(lambda x: np.average(x['Emissions Rate (lbs CO2/MWh)'], weights=x['Generation (MWh)'])).iloc[0]
     
          # Set load-weighted marginal CO2 emissions rate (after) to (before) as baseline. 
          marginal_emissions_rate_after = marginal_emissions_rate_before

          #--- LOCATIONAL MARGINAL PRICE ---#

          # Fetch LMPs. 
          lmp = lmps.loc[lmps['Date'] == hour]['Locational Marginal Price'].iloc[0]

          #--- MARGINAL CO2 EMISSIONS RATE ---#

          if lmp < threshold_price:

               #--- CURTAILMENT ---#

               # If LMP is less than threshold price, wind generation is curtailed.
               wind_gens.loc[wind_gens['Date'] == hour, 'Curtailed'] = True

          elif (marginal_emissions_rate_before != 0) & (wind_gen > marginal_grid_gen):

               #--- CHANGE IN FOSSIL FUEL ON MARGIN ---#
               
               # Pull non-marginal rows in hour from grid generation data.
               non_margin = grid_gens.loc[(grid_gens['Date'] == hour) & (grid_gens['Marginal Flag'] == 'No')]

               # Calculate load-weighted non-marginal CO2 emissions rate.
               non_marginal_emissions_rate = non_margin.groupby('Date').apply(lambda x: np.average(x['Emissions Rate (lbs CO2/MWh)'], weights=x['Generation (MWh)'])).iloc[0]

               # Update marginal CO2 emissions rate (after) to non-marginal CO2 emissions rate.
               marginal_emissions_rate_after = non_marginal_emissions_rate

          # Update marginal CO2 emissions rate (before and after). 
          wind_gens.loc[wind_gens['Date'] == hour, 'Marginal Emissions Rate (lbs CO2/MWh) - Before'] = marginal_emissions_rate_before
          wind_gens.loc[wind_gens['Date'] == hour, 'Marginal Emissions Rate (lbs CO2/MWh) - After'] = marginal_emissions_rate_after

     # Write dataframes to CSV.
     grid_gens.to_csv(grid_gen_file, index=False)
     wind_gens.to_csv(wind_gen_file, index=False)

     return grid_gens, wind_gens

if __name__ == '__main__':

     #--- WIND GENERATION DATA ---#

     # Method #1: Calculate wind generation profile for King Pine from ISO-NE VER data. 
     # wind_inputs = ver()

     # Method #2: Obtain wind generation profile for King Pine using NREL's SAM tool.
     wind_inputs = sam()

     #--- GRID GENERATION DATA ---#

     grid_inputs = None

     # Method #1: Get grid generation by source using EIA's API.
     # if os.path.exists(eia_gen_file):
     #      grid_inputs = pd.read_csv(eia_gen_file)
     # else:
     #      grid_inputs = eia() 

     # Method #2: Get grid generation by source using ISO-NE's dispatch fuel mix data.
     if os.path.exists(iso_gen_file):
          grid_inputs = pd.read_csv(iso_gen_file)
     else: 
          grid_inputs = iso()

     #--- LOCATIONAL MARGINAL PRICES ---#

     lmps = None

     # Get locational marginal price data.
     if os.path.exists(lmp_file):
          lmps = pd.read_csv(lmp_file)
     else:
          lmps = lmp(location_id)

     #--- EMISSIONS IMPACT --#
     grid_output = None
     wind_output = None

     # Calculate emissions impact of King Pine wind farm on ISO-NE grid.
     if os.path.exists(grid_gen_file) & os.path.exists(wind_gen_file):
          grid_output = pd.read_csv(grid_gen_file)
          wind_output = pd.read_csv(wind_gen_file)
     else:
          grid_output, wind_output = emissions(grid_inputs, wind_inputs, lmps)

     # TODO: verify generation totals.
     annual_grid_gen = grid_output['Generation (MWh)'].sum()
     annual_wind_gen = wind_output['Generation (MWh)'].sum()

     print('Annual grid generation (MWh): ', annual_grid_gen)
     print('Annual wind generation (MWh): ', annual_wind_gen)

     # TODO: verify load-weighted marginal CO2 emissions impact. 
     avg_mer_before = wind_output['Marginal Emissions Rate (lbs CO2/MWh) - Before'].mean()
     avg_mer_after = wind_output['Marginal Emissions Rate (lbs CO2/MWh) - After'].mean()
     per_change_mer = (avg_mer_after - avg_mer_before)/(avg_mer_before)*100

     print('Percentage change in marginal CO2 emissions rate: ', per_change_mer)

     # Merges. 
     wind_output = wind_output.merge(lmps, on='Date')

     # TODO: verify curtailment. 
     curtailed = wind_output.loc[wind_output['Curtailed'] == True]
     curtailed_gen = curtailed['Generation (MWh)'].sum()

     print('Curtailed hours: ', len(curtailed))
     print('Curtailed wind generation (MWh): ', curtailed_gen)
     print('Curtailed wind generation (%)', (curtailed_gen/annual_wind_gen)*100)

     #--- VALIDATE ---#

     # TODO: check how often each fuel type is on the margin (both time-weighted and load-weighted).