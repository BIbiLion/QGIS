#ifndef QGSMAPCANVASTRACER_H
#define QGSMAPCANVASTRACER_H

#include "qgstracer.h"

class QAction;
class QgsMapCanvas;
class QgsMessageBar;
class QgsMessageBarItem;

/** \ingroup gui
 * Extension of QgsTracer that provides extra functionality:
 *  - automatic updates of own configuration based on canvas settings
 *  - reporting of issues to the user via message bar
 *
 * A simple registry of tracer instances associated to map canvas instances
 * is kept for convenience. (Map tools do not need to create their local
 * tracer instances and map canvas API is not "polluted" by this optional
 * functionality).
 *
 * @note added in QGIS 2.14
 */
class GUI_EXPORT QgsMapCanvasTracer : public QgsTracer
{
    Q_OBJECT

  public:
    //! Create tracer associated with a particular map canvas, optionally message bar for reporting
    explicit QgsMapCanvasTracer( QgsMapCanvas* canvas, QgsMessageBar* messageBar = 0 );
    ~QgsMapCanvasTracer();

    //! Access to action that user may use to toggle tracing on/off
    QAction* actionEnableTracing() { return mActionEnableTracing; }

    //! Retrieve instance of this class associated with given canvas (if any).
    //! The class keeps a simple registry of tracers associated with map canvas
    //! instances for easier access to the common tracer by various map tools
    static QgsMapCanvasTracer* tracerForCanvas( QgsMapCanvas* canvas );

    //! Report a path finding error to the user
    void reportError( PathError err, bool addingVertex );

  protected:
    //! Sets configuration from current snapping settings and canvas settings
    virtual void configure();

  private slots:
    void onCurrentLayerChanged();

  private:
    QgsMapCanvas* mCanvas;
    QgsMessageBar* mMessageBar;
    QgsMessageBarItem* mLastMessage;

    QAction* mActionEnableTracing;

    static QHash<QgsMapCanvas*, QgsMapCanvasTracer*> sTracers;
};

#endif // QGSMAPCANVASTRACER_H
