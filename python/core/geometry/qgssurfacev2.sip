class QgsSurfaceV2: public QgsAbstractGeometryV2
{
%TypeHeaderCode
#include <qgssurfacev2.h>
%End

  public:
    virtual QgsPolygonV2* surfaceToPolygon() const = 0;
};
