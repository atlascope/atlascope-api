export interface GeoPosition {
    x: number;
    y: number;
    z?: number;
}

interface MouseButtons {
    left: boolean;
    right: boolean;
    middle: boolean;
}

export interface MouseClickEvent {
    data: object;
    mouse: {
        buttonsDown: MouseButtons;
        page: GeoPosition;
    };
}

export interface GeoJSLayer {
  getType: () => string;
  drawLayer: () => void;
  updateLayerUrl: (url: string) => void;
  createFeature: (featureType: string) => GeoJSFeature;
  annotations: () => any[];
  removeAnnotation: (annotation: any) => void;
  removeAllAnnotations: () => void;
  addGeoEventHandler: (event: any, handler: Function) => void;
  mode: (newMode: string | null) => string | null;
}

export interface GeoJSFeature {
  getType: () => string;
  data: (newData: object[]) => void;
  getData: () => object[];
  position: (newPosition: Function) => void;
  style: (newStyle: object | string, newValue?: string) => void;
  draw: () => void;
  featureGcsToDisplay: (x: number, y: number) => GeoPosition;
  registerClickEvent: (handler: Function) => void;
}
