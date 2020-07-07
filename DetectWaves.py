from WaveDetectionFunctions import getAllUserInput
from WaveDetectionFunctions import cleanData
from WaveDetectionFunctions import readFromData
from WaveDetectionFunctions import interpolateData
from WaveDetectionFunctions import drawPlots
from WaveDetectionFunctions import waveletTransform
from WaveDetectionFunctions import findPeaks
from WaveDetectionFunctions import displayProgress
from WaveDetectionFunctions import findPeakRegion
from WaveDetectionFunctions import removePeaks
from WaveDetectionFunctions import updatePlotter
from WaveDetectionFunctions import invertWaveletTransform
from WaveDetectionFunctions import getParameters

import numpy as np
import pywt
import os
import json
import matplotlib.pyplot as plt


########## ACTUAL RUNNING CODE ##########

# First, get applicable user input.
userInput = getAllUserInput()
# Then, iterate over files in data directory
for file in os.listdir( userInput.get('dataSource') ):
    # Import and clean the data, given the file path
    data = cleanData( file, userInput.get('dataSource') )
    if not data.empty:
        launchDateTime, pblHeight = readFromData( file, userInput.get('dataSource'))
        spatialResolution = 5  # meters in between uniformly distributed data points, must be pos integer
        data = interpolateData( data, spatialResolution, pblHeight, launchDateTime )
        if not data.empty:

            if userInput.get('showPlots'):
                drawPlots( data['Alt'], data['T'], data['Dewp.'], pblHeight )
            # Get the stuff... comment better later!
            wavelets = waveletTransform( data, spatialResolution, 'cmor2-6')  # Use morlet wavelet
            # Find local maximums in power surface
            peaks = findPeaks( wavelets.get('power') )
            numPeaks = len(peaks)  # To keep track of progress
            peaksToPlot = peaks.copy()  # Keep peaks for plot at end

            # Numpy array for plotting purposes
            plotter = np.zeros( wavelets.get('power').shape, dtype=bool )

            waves = {'waves': {}}  # Empty dictionary, to contain wave characteristics
            waveCount = 1  # For naming output waves

            # Iterate over local maximums to identify wave characteristics
            while len(peaks) > 0:
                # Output progress to console and increment counter
                displayProgress( peaks, numPeaks )
                # Identify the region surrounding the peak
                region = findPeakRegion( wavelets.get('power'), peaks[0] )

                # Update list of peaks that have yet to be analyzed
                peaks = removePeaks( region, peaks )

                if region.sum().sum() == 1:  # Only found the peak, not the region
                    continue  # Don't bother analyzing the single cell

                # Update plotting mask
                plotter = updatePlotter( region, plotter )

                # Get inverted regional maximums
                wave = invertWaveletTransform( region, wavelets )
                # Get wave parameters
                parameters = getParameters( data, wave, spatialResolution, region )
                if parameters:
                    name = 'wave' + str(waveCount)
                    waves['waves'][name] = parameters
                    waveCount += 1

            # Save waves data here, if saveData boolean is true
            print(waves)
            if userInput.get('saveData'):
                # Save waves data here, if saveData boolean is true
                with open(userInput.get('savePath') + "/" + file[0:-4] + '_wave_parameters.json', 'w') as writeFile:
                    json.dump(waves, writeFile, indent=4, default=str)

            # Also, build nice output plot

            yScale = (2 * np.pi / pywt.scale2frequency('morl', wavelets.get('scales'))) / 1000

            extents = [
                data['Alt'][0] / 1000,
                data['Alt'][len(data['Alt']) - 1] / 1000,
                yScale[0],
                yScale[len(yScale) - 1]
            ]
            plt.figure()
            plt.imshow(wavelets.get('power'),
                       extent=extents)
            plt.axes().set_aspect('auto')
            cb = plt.colorbar()
            plt.contour(data['Alt'] / 1000, np.flip(yScale), plotter,
                        colors='red')
            plt.scatter(data['Alt'][peaksToPlot.T[1]] / 1000, np.flip(yScale)[peaksToPlot.T[0]], marker='.',
                        edgecolors='red')
            plt.xlabel("Altitude [km]")
            plt.ylabel("Vertical Wavelength [km]")
            plt.title("Power surface, including traced peaks")
            cb.set_label("Power [m^2/s^2]")

            if userInput.get('saveData'):
                plt.savefig(userInput.get('savePath') + "/" + file[0:-4] + "_power_surface.png")
            if userInput.get('showPlots'):
                plt.show()
            plt.close()
            print("Finished analysis.")

########## FINISHED ANALYSIS ##########
print("\nAnalyzed all files in folder "+userInput.get('dataSource')+"/")

