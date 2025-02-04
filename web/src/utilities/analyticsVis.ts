import { DetectedStructure } from '@/generatedTypes/AtlascopeTypes';
import { computed } from '@vue/composition-api';
import geo from 'geojs';
import { schemeCategory10 } from 'd3-scale-chromatic';
import { GeoJSLayer } from './composableTypes';
import store from '../store';
import { centroidStringToCoords, NucleusGlandDistance } from './utiltyFunctions';
import { VisOption } from './visualizationTypes';

interface StructurePoint {
  x: number;
  y: number;
  color: string;
  structure: DetectedStructure;
}

const defaultStructureColors = {
  nucleus: 'green',
  gland: 'red',
};

const colors = schemeCategory10;

export function visualizeDetectedStructures(
  vis: VisOption,
  visLayer: GeoJSLayer,
  structures: DetectedStructure[],
) {
  const filteredStructures = structures.filter(
    (structure) => structure.detection_dataset === vis.data.id,
  );
  const structuresPoints = visLayer.createFeature('point');
  const defaultColor = defaultStructureColors[
    vis.data.dataset_type?.replace('_detection', '') as keyof typeof defaultStructureColors
  ];
  const computedLines = computed(() => store.state.nucleiToNearestGlandDistances);
  const allGlands = structures.filter((structure) => structure.structure_type === 'gland').map((struct) => struct.id);

  const centroids = filteredStructures.map(
    (structure) => {
      const centroid = centroidStringToCoords(structure.centroid);
      let distanceLines;
      let customColor;
      if (vis.options.includes('color_by_nearest_gland')) {
        const nearestGland = computedLines.value.find(
          (distance) => distance.nucleus === structure.id,
        )?.gland;
        customColor = colors[allGlands.indexOf(nearestGland) % colors.length];
      }
      if (vis.options.includes('show_distances_on_hover')) {
        distanceLines = computedLines.value.filter(
          (comp: NucleusGlandDistance) => comp[
            structure.structure_type as keyof NucleusGlandDistance
          ] === structure.id,
        ).map(
          (comp: NucleusGlandDistance) => comp.line,
        );
      }

      return {
        x: centroid[0],
        y: centroid[1],
        distanceLines,
        color: customColor || defaultColor,
        originalColor: customColor || defaultColor,
        structure,
      };
    },
  );
  const colorFunc = (point: StructurePoint) => point.color;
  structuresPoints.style({
    radius: 3,
    strokeColor: colorFunc,
    fillColor: colorFunc,
  });
  if (vis.options.includes('show_distances_on_hover')) {
    const distanceLines = visLayer.createFeature('line', {
      style: {
        strokeWidth: 1,
        strokeColor: 'yellow',
      },
    });
    structuresPoints.addGeoEventHandler(geo.event.feature.mouseover, (event: typeof geo.event) => {
      const newData = centroids.map(
        (point) => {
          if (point === event.data) return Object.assign(event.data, { color: 'yellow' });
          return point;
        },
      );
      structuresPoints.data(newData);
      structuresPoints.draw();
      distanceLines.data(event.data.distanceLines);
      distanceLines.draw();
    });
    structuresPoints.addGeoEventHandler(geo.event.feature.mouseout, () => {
      const newData = centroids.map(
        (point) => Object.assign(point, { color: point.originalColor }),
      );
      structuresPoints.data(newData);
      structuresPoints.draw();
      distanceLines.data([]);
      distanceLines.draw();
    });
  }
  structuresPoints.data(
    centroids,
  );
  structuresPoints.draw();

  return true;
}

export default async function visualize(
  visList: VisOption[],
  visLayer: GeoJSLayer,
) {
  const detectedStructures = computed(() => store.state.detectedStuctures);
  if (detectedStructures.value.length < 1) {
    await store.dispatch.fetchDetectedStructures();
  }

  visList.forEach(
    (visOption) => {
      visOption.visFunc(visOption, visLayer, detectedStructures.value);
    },
  );
}
