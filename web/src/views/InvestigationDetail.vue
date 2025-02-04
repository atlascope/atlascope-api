<template>
  <v-container
    class="grey lighten-3 pa-0 ma-0"
    fluid
    fill-height
  >
    <v-row class="ma-2 pa-0">
      <v-col
        class="ma-0 pa-0"
        cols="auto"
      >
        <v-select
          v-if="!loaded || currentDatasets.length > 0"
          :value="rootDataset"
          :items="currentDatasets"
          class="atlascope-dataset-select"
          item-text="name"
          item-value="id"
          return-object
          single-line
          dense
          hide-details
          @input="store.commit.setRootDataset"
        />
        <v-banner
          v-if="loaded && currentDatasets.length === 0"
          single-line
        >
          <v-icon left>
            mdi-alert
          </v-icon>
          No tilesource datasets found for this investigation.
        </v-banner>
        <v-spacer />
      </v-col>
      <v-col cols="auto">
        <investigation-detail-frame-menu />
      </v-col>
    </v-row>
    <v-row class="ma-0 pa-0">
      <v-col class="ma-0 pa-0">
        <v-sheet height="85vh">
          <div
            ref="map"
            class="map"
          />
          <investigation-detail-3-d-vis-menu
            :visible="externalVisualizationMenu"
            :dataset="externalVisualizationMenuDataset"
            :positionx="externalVisualizationMenuX"
            :positiony="externalVisualizationMenuY"
          />
          <v-card
            v-for="note in pinNotes"
            :key="note.id"
            :value="note"
            :class="{'pin-note': true, hidden: !note.showNote || !note.inBounds }"
            :style="{'top': `${note.notePositionY}px`, 'left': `${note.notePositionX}px`}"
          >
            {{ note.note }}
          </v-card>
        </v-sheet>
      </v-col>
      <v-col
        cols="auto"
        class="ma-0 pa-0"
      >
        <v-sheet
          height="85vh"
          color="teal"
        >
          <v-btn
            icon
            @click.stop="toggleSidebar"
          >
            <v-icon v-if="sidebarCollapsed">
              mdi-chevron-left
            </v-icon>
            <v-icon v-else>
              mdi-chevron-right
            </v-icon>
          </v-btn>
          <investigation-sidebar
            v-if="!sidebarCollapsed"
            :similar-nuclei="similarNuclei"
          />
        </v-sheet>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.map {
    width: 100%;
    height: 100%;
    padding: 0;
    margin: 0;
}

.pin-hover-card {
  width: 500px;
}

.pin-note {
  position: absolute;
  max-width: 300px;
  padding: 2px;
  background-color: white;
  border: 1px solid black;
}

.hidden {
  display: none;
}

.frame-row {
  display: inline;
}
</style>

<script lang="ts">
import {
  ref,
  defineComponent,
  onMounted,
  PropType,
  computed,
  watch,
  Ref,
  inject,
} from '@vue/composition-api';
import { schemeCategory10 } from 'd3-scale-chromatic';
import type { AxiosInstance } from 'axios';
import useGeoJSLayer from '../utilities/useGeoJSLayer';
import useGeoJSFeature from '../utilities/useGeoJSFeature';
import { MouseClickEvent, GeoJSLayer, GeoJSFeature } from '../utilities/composableTypes';
import useGeoJS from '../utilities/useGeoJS';
import {
  postGisToPoint,
  Point,
  radiusForZoomLevel,
  opacityForZoomLevel,
} from '../utilities/utiltyFunctions';
import store, { TiffFrame } from '../store';
import InvestigationSidebar from '../components/InvestigationSidebar.vue';
import InvestigationDetailFrameMenu from '../components/InvestigationDetailFrameMenu.vue';
import InvestigationDetail3DVisMenu from '../components/InvestigationDetail3DVisMenu.vue';
import {
  Dataset, Pin, Tour, Waypoint, DetectedStructure,
} from '../generatedTypes/AtlascopeTypes';
import type { DatasetEmbedding } from '../generatedTypes/AtlascopeTypes';

interface RootDatasetEmbedding {
  id: null;
  child_bounding_box: number[];
  parent: null;
  child: number;
}

interface StackFrame {
  embedding: DatasetEmbedding | RootDatasetEmbedding;
  parent: {
    scale: number;
    offset: {
      x: number;
      y: number;
    };
  };
  treeDepth: number;
}

interface PinNote extends Pin {
  showNote: boolean;
  inBounds: boolean;
  notePositionX: number;
  notePositionY: number;
}

interface NonTiledOverlayFeatureData {
  ul: Point;
  lr: Point;
  image: HTMLImageElement;
  pinId: number;
}

interface BandSpec {
  frame: number;
  palette: string;
}

interface TileLayerStyleDict {
  bands: BandSpec[];
}

export interface DetectedStructureWithColor extends DetectedStructure {
  color: string;
}

export default defineComponent({
  name: 'InvestigationDetail',

  components: {
    InvestigationSidebar,
    InvestigationDetailFrameMenu,
    InvestigationDetail3DVisMenu,
  },

  props: {
    investigation: {
      type: String as PropType<string>,
      required: true,
    },
  },

  setup(props) {
    const map: Ref<null | HTMLElement> = ref(null);
    const {
      clampBoundsX,
      exit,
      generatePixelCoordinateParams,
      createMap,
      createLayer,
      geoEvents,
      geoAnnotations,
      geoTransition,
      zoomLevel,
      xCoord,
      yCoord,
      bounds,
    } = useGeoJS(map);
    const loaded = ref(false);
    const sidebarCollapsed = ref(true);
    const hoverText = ref('');
    const externalVisualizationMenu = ref(false);
    const externalVisualizationMenuX = ref(0);
    const externalVisualizationMenuY = ref(0);
    const externalVisualizationMenuDataset: Ref<Dataset | null> = ref(null);

    function toggleSidebar() {
      sidebarCollapsed.value = !sidebarCollapsed.value;
    }

    const rootDataset = computed(() => store.state.rootDataset);
    const showEmbeddings = computed(() => store.state.showEmbeddings);
    const currentDatasets = computed(() => store.state.currentDatasets);
    const selectionMode = computed(() => store.state.selectionMode);
    let selectionLayer: GeoJSLayer | undefined;
    let featureLayer: GeoJSLayer | undefined;
    let pinFeature: GeoJSFeature | undefined;
    let tourPointsFeature: GeoJSFeature | undefined;
    let tourLineFeature: GeoJSFeature | undefined;
    /* eslint-disable */
    let nonTiledOverlayFeature: any;
    /* eslint-enable */
    let rootDatasetLayer: GeoJSLayer;
    const pinNotes: Ref<PinNote[]> = ref([]);
    const frames: Ref<TiffFrame[]> = computed(() => store.state.rootDatasetFrames);

    function setVisualizationLayer() {
      store.commit.setVisualizationLayer(createLayer(
        'feature',
        { features: ['grid', 'point', 'line', 'polygon', 'quad.image'] },
      ));
    }

    function getSelectedFrameStyle(): BandSpec[] {
      return frames.value.filter((frame: TiffFrame) => frame.displayed).map((frame: TiffFrame) => ({
        frame: frame.frame,
        palette: `${frame.color}`,
      }));
    }

    function buildUrlQueryArgs() {
      if (frames.value.length === 0) {
        return '';
      }
      const style: TileLayerStyleDict = {
        bands: getSelectedFrameStyle(),
      };
      const encodedStyle = encodeURIComponent(JSON.stringify(style));
      return `?style=${encodedStyle}`;
    }

    function tearDownMap() {
      exit();
      selectionLayer = undefined;
      featureLayer = undefined;
      pinFeature = undefined;
    }

    function isPin(obj: object): obj is Pin {
      return (
        'id' in obj
        && 'location' in obj
        && 'minimum_zoom' in obj
        && 'maximum_zoom' in obj
      );
    }

    function movePinNoteCards() {
      if (!featureLayer || !pinFeature || !map.value) {
        return;
      }
      pinFeature.getData().forEach((pin: object) => {
        if (!pinFeature) {
          return;
        }
        if (isPin(pin)) {
          const { x, y } = postGisToPoint(pin.location) || { x: 0, y: 0 };
          const newScreenCoords = pinFeature.featureGcsToDisplay(x, y);
          const note = pinNotes.value.find((pinNote) => pinNote.id === pin.id);
          const {
            left, top, width, height,
          } = map.value?.getBoundingClientRect() || {
            left: 0, top: 0, width: 0, height: 0,
          };
          if (note) {
            note.notePositionX = newScreenCoords.x + left;
            note.notePositionY = newScreenCoords.y + top;
            if (note.notePositionX > left + width
                || note.notePositionY > top + height
                || note.notePositionX < left
                || note.notePositionY < top
                || radiusForZoomLevel(
                  zoomLevel.value,
                  pin.minimum_zoom || 0,
                  pin.maximum_zoom || 40,
                ) === 0
                || opacityForZoomLevel(zoomLevel.value, pin.maximum_zoom || 40) === 0) {
              note.inBounds = false;
            } else {
              note.inBounds = true;
            }
          }
        }
      });
    }

    function showHidePinsForZoomLevel(level: number) {
      if (pinFeature) {
        pinFeature.style('radius', (pin: Pin) => (
          radiusForZoomLevel(level, pin.minimum_zoom, pin.maximum_zoom)
        ));
        pinFeature.style('fillOpacity', (pin: Pin) => (
          opacityForZoomLevel(level, pin.maximum_zoom)
        ));
        pinFeature.style('strokeOpacity', (pin: Pin) => (
          opacityForZoomLevel(level, pin.maximum_zoom)
        ));
        pinFeature.draw();
      }
    }

    watch([xCoord, yCoord, zoomLevel], () => {
      showHidePinsForZoomLevel(zoomLevel.value);
      movePinNoteCards();
    });

    watch(zoomLevel, (newZoom) => {
      store.commit.setZoomLevel(newZoom);
    });

    watch(bounds, (newBounds) => {
      store.commit.setBounds(newBounds);
    });

    function drawMap(dataset: Dataset | null) {
      tearDownMap();
      if (!dataset || !dataset.id) {
        return;
      }

      const apiRoot = process.env.VUE_APP_API_ROOT;
      const embeddings = showEmbeddings.value ? store.state.datasetEmbeddings : [];
      const rootDatasetID = dataset.id;
      const rootTileMetadata = store.state.datasetTileMetadata[rootDatasetID];

      if (
        rootTileMetadata === undefined
        || rootTileMetadata.size_x === undefined
        || rootTileMetadata.size_y === undefined
        || rootTileMetadata.tile_size === undefined
        || rootTileMetadata.levels === undefined
      ) {
        return;
      }

      const rootPixelParams = generatePixelCoordinateParams(
        rootTileMetadata.size_x || 0,
        rootTileMetadata.size_y || 0,
        rootTileMetadata.tile_size || 0,
        rootTileMetadata.tile_size || 0,
      );
      const mapParams = {
        ...rootPixelParams.map,
        max: 40,
      };
      const rootLayerParams = {
        ...rootPixelParams.layer,
        zIndex: 0,
        url: `${apiRoot}/datasets/tile_source/${rootDatasetID}/tiles/{z}/{x}/{y}.png`,
        crossDomain: 'use-credentials',
      };
      createMap(mapParams);
      rootDatasetLayer = createLayer('osm', rootLayerParams);

      const visited: Set<RootDatasetEmbedding | DatasetEmbedding> = new Set();
      const stack: Array<StackFrame> = [];
      /* eslint-disable */
      stack.unshift(
        ...embeddings
          .filter((e) => e.parent === rootDatasetID)
          .map((e) => ({
            embedding: e,
            parent: { scale: 1, offset: { x: 0, y: 0 } },
            treeDepth: 1,
          })),
      );

      while (stack.length > 0) {
        const { embedding, parent, treeDepth } = stack.shift()!;
        /* eslint-enable */
        if (!visited.has(embedding)) {
          visited.add(embedding);

          if (
            embedding === undefined
            || embedding.child_bounding_box === undefined
            || embedding.child_bounding_box.length !== 4
          ) {
            return;
          }

          const datasetID = embedding.child;
          const tileMetadata = store.state.datasetTileMetadata[datasetID];

          if (
            tileMetadata === undefined
            || tileMetadata.size_x === undefined
            || tileMetadata.size_y === undefined
            || tileMetadata.tile_size === undefined
            || tileMetadata.levels === undefined
          ) {
            return;
          }

          const boundingBox = {
            x: {
              min: embedding.child_bounding_box[0],
              max: embedding.child_bounding_box[2],
            },
            y: {
              min: embedding.child_bounding_box[1],
              max: embedding.child_bounding_box[3],
            },
          };
          const scale = Math.min(
            (parent.scale * (boundingBox.x.max - boundingBox.x.min))
              / tileMetadata.size_x,
            (parent.scale * (boundingBox.y.max - boundingBox.y.min))
              / tileMetadata.size_y,
          );
          const offset = {
            x: (parent.scale / scale) * (parent.offset.x + boundingBox.x.min),
            y: (parent.scale / scale) * (parent.offset.y + boundingBox.y.min),
          };
          const pixelParams = generatePixelCoordinateParams(
            tileMetadata.size_x || 0,
            tileMetadata.size_y || 0,
            tileMetadata.tile_size || 0,
            tileMetadata.tile_size || 0,
          );
          const layerParams = {
            ...pixelParams.layer,
            zIndex: treeDepth,
            url: `${apiRoot}/datasets/tile_source/${datasetID}/tiles/{z}/{x}/{y}.png`,
            crossDomain: 'use-credentials',
          };
          createLayer(
            'osm',
            layerParams,
            `+proj=longlat +axis=enu +xoff=-${offset.x} +yoff=${
              offset.y
            } +s11=${1 / scale} +s22=${1 / scale}`,
          );

          /* eslint-disable */
          const frontier = embeddings.filter((e) => e.parent === datasetID);
          stack.unshift(
            ...frontier.map((e) => ({
              embedding: e,
              parent: { scale, offset },
              treeDepth: treeDepth + 1,
            })),
          );
          /* eslint-enable */
        }
      }
      clampBoundsX(false);
    }

    const similarNuclei: Ref<Array<DetectedStructureWithColor>> = ref([]);
    const axios = inject('axios') as AxiosInstance;
    function colorSimilarNuclei(nuclei: Array<DetectedStructure>) {
      const colors = schemeCategory10;
      const nucleiWithColor: Array<DetectedStructureWithColor> = [];
      for (let i = 0; i < nuclei.length; i += 1) {
        const nucleus = nuclei[i];
        const nucleusWithColor = { ...nucleus, color: colors[i] };
        nucleiWithColor.push(nucleusWithColor);
      }
      return nucleiWithColor;
    }
    function setupSimilarNuclei() {
      const layer = createLayer(
        'feature',
        { features: ['marker'] },
      ) as ReturnType<typeof useGeoJSLayer>;
      layer.addGeoEventHandler(geoEvents.mouseclick, async (event: MouseClickEvent['mouse']) => {
        const { x, y } = event.geo;
        if (!rootDataset.value) {
          return;
        }
        const url = `/similar-nuclei/${rootDataset.value.id}/${x}/${y}/`;
        const resp = await axios.get(url);
        similarNuclei.value = colorSimilarNuclei(resp.data);
        layer.clearFeatures();
        const feature = layer.createFeature('marker') as ReturnType<typeof useGeoJSFeature>;
        feature.data(similarNuclei.value);
        feature.position((nucleus: DetectedStructureWithColor) => (
          postGisToPoint(nucleus.centroid)
        ));
        feature.style({
          symbol: 64,
          symbolValue: 1 / 3,
          rotation: -Math.PI / 2,
          radius: 30,
          strokeWidth: 0,
          strokeColor: 'blue',
          fillColor: (nucleus: DetectedStructureWithColor) => nucleus.color,
          rotateWithMap: false,
        });
        feature.draw();
      });
      layer.drawLayer();
    }

    watch(rootDataset, (newValue) => {
      drawMap(newValue);
      setupSimilarNuclei();
      similarNuclei.value = [];
    });

    watch(showEmbeddings, () => {
      drawMap(rootDataset.value);
    });

    watch(frames, () => {
      if (rootDataset.value && rootDatasetLayer) {
        const queryString = buildUrlQueryArgs();
        const apiRoot = process.env.VUE_APP_API_ROOT;
        const datasetId = rootDataset.value.id;
        const newUrl = `
          ${apiRoot}/datasets/tile_source/${datasetId}/tiles/{z}/{x}/{y}.png${queryString}
        `;
        rootDatasetLayer.updateLayerUrl(newUrl);
        rootDatasetLayer.drawLayer();
      }
    }, { deep: true });

    function handleSelectionChange() {
      if (selectionLayer === undefined) return;
      const annotations = selectionLayer.annotations();
      /* eslint-disable-next-line */
      annotations.forEach((annotation: any) => {
        if (selectionLayer === undefined) return;
        annotation.style({
          fillColor: '#00796b',
          strokeColor: '#00796b',
        });
        if (annotation.state() !== geoAnnotations.state.create) {
          if (annotations.length > 1) {
            selectionLayer.removeAnnotation(annotation);
          } else {
            const corners = annotation.coordinates();
            const newSelection = [
              corners[1].x, corners[1].y, corners[3].x, corners[3].y,
            ].map(
              (num) => Math.round(num),
            );
            store.commit.setSubimageSelection(newSelection);
          }
        }
      });
    }

    watch(selectionMode, () => {
      if (!selectionLayer) {
        selectionLayer = createLayer('annotation', {
          annotations: ['rectangle'],
          showLabels: false,
        });
        if (!selectionLayer) return;
        selectionLayer.addGeoEventHandler(geoEvents.annotation.add, handleSelectionChange);
        selectionLayer.addGeoEventHandler(geoEvents.annotation.update, handleSelectionChange);
        selectionLayer.addGeoEventHandler(geoEvents.annotation.remove, handleSelectionChange);
        selectionLayer.addGeoEventHandler(geoEvents.annotation.state, handleSelectionChange);
      }
      if (!selectionMode.value) {
        selectionLayer.mode(null);
        selectionLayer.removeAllAnnotations();
        store.commit.setSubimageSelection(null);
      } else {
        selectionLayer.mode('rectangle');
      }
    });

    const selectedPins: Ref<Pin[]> = computed(() => store.state.selectedPins);
    const selectedTour: Ref<Tour> = computed(() => store.state.selectedTour);
    const selectedWaypoint: Ref<Waypoint> = computed(() => store.state.selectedWaypoint);
    // Create note cards for any pins without a child dataset.
    function createPinNotes() {
      const noteOnlyPins = store.state.currentPins.filter(
        (pin: Pin) => pin.pin_type === 'NotePin',
      );
      pinNotes.value = noteOnlyPins.map((pin) => ({
        ...pin,
        showNote: false,
        inBounds: pin.minimum_zoom === 0,
        notePositionX: 0,
        notePositionY: 0,
      }));
    }

    async function toggleNonTiledImageOverlay(pin: Pin, dataset: Dataset) {
      if (!dataset.content) {
        throw new Error(`Expected dataset of type ${dataset.dataset_type} to have content`);
      }
      if (!featureLayer) {
        throw new Error('Expected a featureLayer to exist');
      }
      if (!store.state.axiosInstance) {
        throw new Error('Expected the store to contain an axios object for feteching metadata');
      }
      if (!nonTiledOverlayFeature) {
        nonTiledOverlayFeature = featureLayer.layer.value.createFeature('quad');
      }
      const quadData: NonTiledOverlayFeatureData[] = nonTiledOverlayFeature.data() || [];
      const existingOverlay = quadData.find(
        (overlay: NonTiledOverlayFeatureData) => overlay.pinId === pin.id,
      );
      if (existingOverlay) {
        nonTiledOverlayFeature.data(
          nonTiledOverlayFeature.data().filter(
            (overlay: NonTiledOverlayFeatureData) => overlay.pinId !== pin.id,
          ),
        ).draw();
        nonTiledOverlayFeature.draw();
      } else {
        const urlRoot = process.env.VUE_APP_API_ROOT;
        const url = `${urlRoot}/datasets/tile_source/${dataset.id}/data/thumbnail.png`;
        const image: HTMLImageElement = new Image();
        image.src = url;
        image.crossOrigin = 'use-credentials';
        const imageMetadata = (await store.state.axiosInstance.get(`${urlRoot}/datasets/tile_source/${dataset.id}/info/metadata`)).data;
        const ul = postGisToPoint(pin.location);
        const lr = {
          x: ul.x + (imageMetadata.sizeX || 0),
          y: ul.y + (imageMetadata.sizeY || 0),
        };
        quadData.push({
          ul,
          lr,
          image,
          pinId: pin.id,
        });
        nonTiledOverlayFeature.data(quadData).draw();
      }
    }

    function toggle3DVolumePin(pin: Pin, dataset: Dataset) {
      if (!pinFeature) {
        throw new Error('Pin feature must exist before pins can be clicked.');
      }
      const { x, y } = postGisToPoint(pin.location);
      const newMenuCoordinates = pinFeature.featureGcsToDisplay(x, y);
      externalVisualizationMenu.value = !externalVisualizationMenu.value;
      externalVisualizationMenuX.value = newMenuCoordinates.x;
      externalVisualizationMenuY.value = newMenuCoordinates.y;
      externalVisualizationMenuDataset.value = dataset;
    }

    function toggleDatasetPin(pin: Pin) {
      const childDataset: Dataset | undefined = store.state.currentDatasets.find(
        (dataset: Dataset) => dataset.id === pin.child,
      );
      if (!childDataset) return;
      switch (childDataset.dataset_type) {
        case 'non_tiled_image':
          toggleNonTiledImageOverlay(pin, childDataset).catch((err) => {
            if (err.response) {
              throw new Error(`Unable to fetch metadata for dataset ${childDataset.id}`);
            } else {
              throw err;
            }
          });
          break;
        case '3d_volume':
          toggle3DVolumePin(pin, childDataset);
          break;
        default:
          break;
      }
    }

    watch(selectedPins, (newPins, oldPins) => {
      if (!featureLayer) {
        featureLayer = createLayer(
          'feature',
          { features: ['grid', 'point', 'line', 'polygon', 'quad.image'] },
        );
      }
      if (!featureLayer) {
        return;
      }
      const newPinIds = newPins.map((pin) => pin.id);
      const removedPinIds = oldPins.filter((pin: Pin) => !newPinIds.includes(pin.id))
        .map((pin: Pin) => pin.id);
      if (nonTiledOverlayFeature) {
        const overlayData = nonTiledOverlayFeature.data();
        const newOverlayData = overlayData.filter(
          (overlay: NonTiledOverlayFeatureData) => !removedPinIds.includes(overlay.pinId),
        );
        nonTiledOverlayFeature.data(newOverlayData).draw();
      }
      removedPinIds.forEach((pinId) => {
        const note = pinNotes.value.find((pinNote) => pinNote.id === pinId);
        if (note) {
          note.showNote = false;
        }
      });
      if (!pinFeature) {
        pinFeature = featureLayer.createFeature('point');
        pinFeature.data(selectedPins.value);
        pinFeature.position((pin: Pin) => postGisToPoint(pin.location));
        pinFeature.style({
          radius: 10,
          strokeColor: 'white',
          fillColor: (pin: Pin) => pin.color,
        });
        pinFeature.draw();
        pinFeature.addGeoEventHandler(geoEvents.feature.mouseclick, (event: MouseClickEvent) => {
          if (!map.value) { return; }

          if (event.mouse.buttonsDown.left) {
            const pinClicked = event.data as Pin;
            if (pinClicked.pin_type === 'NotePin') {
              const noteToToggle = pinNotes.value.find((note) => note.id === pinClicked.id);
              if (noteToToggle) {
                noteToToggle.showNote = !noteToToggle.showNote;
                noteToToggle.notePositionX = event.mouse.page.x;
                noteToToggle.notePositionY = event.mouse.page.y;
              }
            } else if (pinClicked.pin_type === 'DatasetPin') {
              toggleDatasetPin(pinClicked);
            }
          }
        });
      } else {
        pinFeature.data(selectedPins.value);
        pinFeature.draw();
      }
      showHidePinsForZoomLevel(zoomLevel.value);
    });

    watch(selectedTour, () => {
      if (!featureLayer) {
        featureLayer = createLayer(
          'feature',
          { features: ['point', 'line', 'polygon', 'quad.image'] },
        );
      }
      if (!featureLayer) {
        return;
      }
      if (!tourPointsFeature) {
        tourPointsFeature = featureLayer.createFeature('point');
        tourPointsFeature.data(selectedTour.value.waypoints);
        tourPointsFeature.position(
          (waypoints: Waypoint) => (postGisToPoint(waypoints.location as string)),
        );

        tourPointsFeature.style({
          radius: 10,
          strokeColor: 'blue',
          fillColor: 'blue',
        });
        tourPointsFeature.draw();
      } else {
        tourPointsFeature.data(selectedTour.value.waypoints);
        tourPointsFeature.position(
          (waypoints: Waypoint) => (postGisToPoint(waypoints.location as string)),
        );

        tourPointsFeature.draw();
      }
      if (!tourLineFeature) {
        tourLineFeature = featureLayer.createFeature('line');
        tourLineFeature.data(
          [
            selectedTour.value.waypoints.map(
              (element) => postGisToPoint(element.location as string),
            ),
          ],
        );
        tourLineFeature.style({
          strokeWidth: 5,
          strokeColor: 'blue',
        });
        tourLineFeature.draw();
      } else {
        tourLineFeature.data(
          [
            selectedTour.value.waypoints.map(
              (element) => postGisToPoint(element.location as string),
            ),
          ],
        );
        tourLineFeature.draw();
      }
    }, { deep: true });

    watch(selectedWaypoint, () => {
      geoTransition(postGisToPoint(selectedWaypoint.value.location as string),
        2000,
        selectedWaypoint.value.zoom);
    });

    onMounted(async () => {
      await store.dispatch.fetchCurrentInvestigation(props.investigation);
      drawMap(store.state.rootDataset);
      store.commit.setBounds(bounds.value);
      createPinNotes();
      setupSimilarNuclei();
      loaded.value = true;
      await store.dispatch.fetchDetectedStructures();
      setVisualizationLayer();
    });

    return {
      loaded,
      sidebarCollapsed,
      hoverText,
      toggleSidebar,
      map,
      currentDatasets,
      rootDataset,
      selectedPins,
      pinNotes,
      store,
      externalVisualizationMenu,
      externalVisualizationMenuX,
      externalVisualizationMenuY,
      externalVisualizationMenuDataset,
      similarNuclei,
    };
  },
});
</script>
