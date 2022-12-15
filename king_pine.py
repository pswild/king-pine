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

from reV.config.project_points import ProjectPoints
from reV.generation.generation import Gen

# Silence warnings...
pd.options.mode.chained_assignment = None

# API keys. 
NREL_API_KEY = 'yqjUGnkgdH4m8XrGh6OXi8rK7JMLJh6q3PafSMls'
EIA_API_KEY = 'GbKYer2Pz9JS0UttTjwxahbfN5ZzDKE0ZuyjsJQY'

# Coordinates of King Pine wind farm.
lat = 46.918
lon = -68.169

# Nameplate capacity (MW). 
nameplate_cap = 1000

# --- PATH ---# 

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

#--- OUTPUT ---# 

# ISO-NE generated emissions profile. 
generated_emissions_file = os.path.join(here, 'output/generated_emissions_profile.csv')

# King Pine avoided emissions profile. 
avoided_emissions_file = os.path.join(here, 'output/avoided_emissions_profile.csv')

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

def rev():
     '''Run reV model to obtain capacity factor profile for King Pine wind farm.'''

     # TODO: retrieve relevant wind resource file from WIND Toolkit via wtk().
     # TODO: download SAM configuration file that matches wind farm specifications. 
          
     # Array of coordinates.
     lat_lons = np.array([[lat, lon]])

     # Create Project Points.
     pp = ProjectPoints.lat_lon_coords(lat_lons, res_file, sam_file)

     # Run reV.
     results = Gen.reV_run('windpower', pp, sam_file, res_file, max_workers=1, out_fpath=None, output_request=('cf_profile'))

     # Convert capacity factor profile into generation profile. 
     gen = results.out['cf_profile'] * nameplate_cap
     
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

     # Counter.
     i = 1

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

          # Increment counter. 
          i += 1
     
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

def emissions(new_gen, grid_gen):
     '''Calculates the emissions impact of the King Pine wind farm.'''

     # Dictionary of CO2 emissions rates (lbs CO2/MWh) for EPA eGRID's NPCC New England subregion (NEWE) in 2020. 
     co2_emissions_rates = {
          'Oil': 3374.668,
          'Coal': 2277.021,
          'Natural Gas': 850.537,
          'Refuse': 0.0, # biomass is part of carbon cycle
          'Wood': 0.0, # biomass is part of carbon cycle
          'Landfill Gas': 0.0, # no additional carbon emissions because flared otherwise
          'Nuclear': 0.0,
          'Hydro': 0.0,
          'Solar': 0.0,
          'Wind': 0.0,
          'Other': 0.0 # energy storage and demand response
     }

     # Map CO2 emissions rates by fuel type.
     grid_gen['Emissions Rate (lbs CO2/MWh)'] = grid_gen['Fuel Category'].map(co2_emissions_rates)

     # Add column for CO2 emissions to grid generation.
     grid_gen['Emissions (lbs CO2)'] = grid_gen['Generation (MWh)'] * grid_gen['Emissions Rate (lbs CO2/MWh)']

     # Add column for CO2 emissions avoided per hour to new generation. 
     new_gen['Avoided Emissions (lbs CO2)'] = 0

     # Identify marginal fuel type for each hour.
     for hour in grid_gen['Date'].unique():

          # Get new generation for hour. 
          new_gen_hr = new_gen.loc[new_gen['Date'] == hour]['Generation (MWh)'].iloc[0]

          # Pull slice of hour from grid generation data. 
          slice = grid_gen.loc[(grid_gen['Date'] == hour) & (grid_gen['Marginal Flag'] == 'Yes')]

          if slice.empty:

               # NOTE: If no marginal fuel type indicated, default to natural gas. 
               slice = grid_gen.loc[(grid_gen['Date'] == hour) & (grid_gen['Fuel Category'] == 'Natural Gas')]

          # Get grid generation for hour and emissions rate.
          marginal_grid_gen_hr = slice['Generation (MWh)'].iloc[0]
          marginal_emissions_rate = slice['Emissions Rate (lbs CO2/MWh)'].iloc[0]
     
          # Hourly avoided CO2 emissions.
          hourly_avoided_emissions = 0

          # Check if new generation exceeds grid generation from marginal fuel type. 
          if new_gen_hr > marginal_grid_gen_hr:
               
               # Multiply CO2 emissions rate of marginal fuel type by grid generation from marginal fuel type. 
               emissions_comp_1 = marginal_emissions_rate * marginal_grid_gen_hr

               # Expand slice to other fuel types.
               slice = grid_gen.loc[grid_gen['Date'] == hour]

               # Calculate weighted average CO2 emissions rate of remaining generation.
               avg_emissions_rate_remainder = slice.groupby('Date').apply(lambda x: np.average(x['Emissions Rate (lbs CO2/MWh)'], weights=x['Generation (MWh)'])).iloc[0]

               # Multiply average CO2 emissions rate of remaining fuel types by remainder of new generation.
               emissions_comp_2 = avg_emissions_rate_remainder * (new_gen_hr - marginal_grid_gen_hr)

               # Sum both components of hourly avoided CO2 emissions. 
               hourly_avoided_emissions = emissions_comp_1 + emissions_comp_2

          else: 

               # Multiply CO2 emissions rate of marginal fuel type by new generation. 
               hourly_avoided_emissions = marginal_emissions_rate * new_gen_hr

          # Update hourly avoided CO2 emissions. 
          new_gen.loc[new_gen['Date'] == hour, 'Avoided Emissions (lbs CO2)'] = hourly_avoided_emissions

     # Calculate annual generated CO2 emissions. 
     annual_generated_emissions = grid_gen['Emissions (lbs CO2)'].sum()

     # Calaculate annual avoided CO2 emissions.
     annual_avoided_emissions = new_gen['Avoided Emissions (lbs CO2)'].sum()

     # Write dataframes to CSV.
     grid_gen.to_csv(generated_emissions_file, index=False)
     new_gen.to_csv(avoided_emissions_file, index=False)

     return annual_avoided_emissions, annual_generated_emissions

if __name__ == '__main__':

     #--- WIND GENERATION DATA ---#

     # Method #1: Obtain wind generation profile for King Pine using NREL's reV tool.
     # wind_gen = rev()

     # Method #2: Obtain wind generation profile for King Pine using NREL's SAM tool.
     wind_gen = sam()

     # Method #3: Calculate wind generation profile for King Pine from ISO-NE VER data. 
     # wind_gen = ver()

     #--- GRID GENERATION DATA ---#

     grid_gen = None

     # Method #1: Get grid generation by source using EIA's API.
     # if os.path.exists(eia_gen_file):
     #      grid_gen = pd.read_csv(eia_gen_file)
     # else:
     #      grid_gen = eia() 

     # Method #2: Get grid generation by source using ISO-NE's dispatch fuel mix data.
     if os.path.exists(iso_gen_file):
          grid_gen = pd.read_csv(iso_gen_file)
     else: 
          grid_gen = iso()

     #--- EMISSIONS IMPACT --#

     # Calculate emissions impact of King Pine wind farm on ISO-NE grid.
     annual_avoided_emissions, annual_generated_emissions = emissions(wind_gen, grid_gen)

     #--- ANALYSIS ---# 

     # TODO: verify generation totals.
     annual_wind_gen = wind_gen['Generation (MWh)'].sum()
     annual_grid_gen = grid_gen['Generation (MWh)'].sum()

     print('Annual generation by King Pine wind farm (MWh): ', annual_wind_gen)
     print('Annual generation by ISO-NE grid (MWh): ', annual_grid_gen)

     # TODO: verify emissions rates and reductions.
     avg_co2_emissions_avoided = (annual_avoided_emissions)/(annual_wind_gen)
     avg_co2_emissions_generated = (annual_generated_emissions)/(annual_grid_gen)

     print('Average CO2 emissions avoided by King Pine generation (lbs CO2/MWh): ', avg_co2_emissions_avoided)
     print('Average CO2 emission generated by ISO-NE generation (lbs CO2/MWh): ', avg_co2_emissions_generated)

     # NOTE: EPA's eGRID average CO2 emissions rate for electricity generation in NEWE subregion was 528.24 lbs CO2/MWh. 

     #--- VALIDATE ---#

     # TODO: check how often each fuel type is on the margin (both time-weighted and load-weighted).