// Copyright 2008 Nanorex, Inc.  See LICENSE file for details.

#include <fstream>
#include <sstream>
#include <cassert>
#include <set>

#include "glt_bbox.h"

// #include "Nanorex/Interface/NXSceneGraph.h"
#include "Nanorex/Interface/NXEntityManager.h"
// #include "Nanorex/Interface/NXAtomRenderData.h"
// #include "Nanorex/Interface/NXBondRenderData.h"
//#include "Nanorex/Interface/NXOpenGLRendererPlugin.h"

// #include <openbabel/atom.h>
// #include <openbabel/bond.h>
#include <openbabel/mol.h>

#include "NXOpenGLRenderingEngine.h"

using namespace std;
using namespace OpenBabel;


namespace Nanorex {

NXOpenGLRenderingEngine::NXOpenGLRenderingEngine(QWidget *parent)
    : QGLWidget(parent),
    NXRenderingEngine(),
    camera(this),
    rootSceneGraphNode(NULL),
    pluginList(),
    currentPluginIter(),
    lights(),
    lightModel(),
    // isOrthographicProjection(false),
    // orthographicProjection(),
    // perspectiveProjection(),
    // viewport(),
    elementColorMap(),
    defaultAtomMaterial(),
    defaultBondMaterial()
{
    bool ok = true;
    
    ok = initializeElementColorMap();
    /// @todo trap error
    initializeDefaultMaterials();
}


NXOpenGLRenderingEngine::~NXOpenGLRenderingEngine()
{
}


bool NXOpenGLRenderingEngine::initializeElementColorMap(void)
{
    elementColorMap.clear();
    elementColorMap[0] = NXRGBColor(204,0,0,255);
    elementColorMap[1] = NXRGBColor(199,199,199,255);
    elementColorMap[2] = NXRGBColor(107,115,140,255);
    elementColorMap[3] = NXRGBColor(0,128,128,255);
    elementColorMap[4] = NXRGBColor(250,171,255,255);
    elementColorMap[5] = NXRGBColor(51,51,150,255);
    elementColorMap[6] = NXRGBColor(99,99,99,255);
    elementColorMap[7] = NXRGBColor(31,31,99,255);
    elementColorMap[8] = NXRGBColor(128,0,0,255);
    elementColorMap[9] = NXRGBColor(0,99,51,255);
    elementColorMap[10] = NXRGBColor(107,115,140,255);
    elementColorMap[11] = NXRGBColor(0,102,102,255);
    elementColorMap[12] = NXRGBColor(224,153,230,255);
    elementColorMap[13] = NXRGBColor(128,128,255,255);
    elementColorMap[14] = NXRGBColor(41,41,41,255);
    elementColorMap[15] = NXRGBColor(84,20,128,255);
    elementColorMap[16] = NXRGBColor(219,150,0,255);
    elementColorMap[17] = NXRGBColor(74,99,0,255);
    elementColorMap[18] = NXRGBColor(107,115,140,255);
    elementColorMap[19] = NXRGBColor(0,77,77,255);
    elementColorMap[20] = NXRGBColor(201,140,204,255);
    elementColorMap[21] = NXRGBColor(106,106,130,255);
    elementColorMap[22] = NXRGBColor(106,106,130,255);
    elementColorMap[23] = NXRGBColor(106,106,130,255);
    elementColorMap[24] = NXRGBColor(106,106,130,255);
    elementColorMap[25] = NXRGBColor(106,106,130,255);
    elementColorMap[26] = NXRGBColor(106,106,130,255);
    elementColorMap[27] = NXRGBColor(106,106,130,255);
    elementColorMap[28] = NXRGBColor(106,106,130,255);
    elementColorMap[29] = NXRGBColor(106,106,130,255);
    elementColorMap[30] = NXRGBColor(106,106,130,255);
    elementColorMap[31] = NXRGBColor(153,153,204,255);
    elementColorMap[32] = NXRGBColor(102,115,26,255);
    elementColorMap[33] = NXRGBColor(153,66,179,255);
    elementColorMap[34] = NXRGBColor(199,79,0,255);
    elementColorMap[35] = NXRGBColor(0,102,77,255);
    elementColorMap[36] = NXRGBColor(107,115,140,255);
    elementColorMap[51] = NXRGBColor(153,66,179,255);
    elementColorMap[52] = NXRGBColor(230,89,0,255);
    elementColorMap[53] = NXRGBColor(0,128,0,255);
    elementColorMap[54] = NXRGBColor(102,115,140,255);
    elementColorMap[200] = NXRGBColor(102,102,204,255);
    elementColorMap[201] = NXRGBColor(102,204,102,255);
    elementColorMap[202] = NXRGBColor(102,26,128,255);
    elementColorMap[203] = NXRGBColor(102,204,204,255);
    elementColorMap[204] = NXRGBColor(102,102,204,255);
    elementColorMap[205] = NXRGBColor(102,26,128,255);
    elementColorMap[206] = NXRGBColor(102,204,102,255);
    elementColorMap[207] = NXRGBColor(77,179,77,255);
    return true;
        
#if 0 // read from file - sensitive to location
    /// @todo Remove filename hardcoding
    ifstream elemColorMapFile("default-element-colors.txt", ios::in);
    if(!elemColorMapFile)
        return false;
    while(elemColorMapFile.good()) {
        int const LINEBUF_SIZE = 201;
        char linebuf[LINEBUF_SIZE];
        elemColorMapFile.getline(linebuf, LINEBUF_SIZE);
        assert((int)elemColorMapFile.gcount() < LINEBUF_SIZE);
        
        istringstream line(linebuf);
        // ignore comment lines
        if(line.peek() == '#') continue;
        unsigned int element(-1), rgbColor[3];
        line >> element;
        // trap blank last line effect
        if(element == (unsigned int)-1) break;
        line >> rgbColor[0] >> rgbColor[1] >> rgbColor[2];
        GltColor elementColor(double(rgbColor[0])/255.0, double(rgbColor[1])/255.0, double(rgbColor[2])/255.0);
        elementColorMap[element] = elementColor;
    }
#endif
}


void NXOpenGLRenderingEngine::initializeDefaultMaterials(void)
{
    defaultAtomMaterial.face = GL_FRONT;
    defaultAtomMaterial.ambient[0] = 1.0f;
    defaultAtomMaterial.ambient[1] = 1.0f;
    defaultAtomMaterial.ambient[2] = 1.0f;
    defaultAtomMaterial.ambient[3] = 1.0f;
    
    defaultAtomMaterial.diffuse[0] = 1.0f;
    defaultAtomMaterial.diffuse[1] = 1.0f;
    defaultAtomMaterial.diffuse[2] = 1.0f;
    defaultAtomMaterial.diffuse[3] = 1.0f;
    
    defaultAtomMaterial.specular[0] = 0.5f;
    defaultAtomMaterial.specular[1] = 0.5f;
    defaultAtomMaterial.specular[2] = 0.5f;
    defaultAtomMaterial.specular[3] = 1.0f;
    
    defaultAtomMaterial.shininess = 35.0;
    
    defaultAtomMaterial.emission[0] = 0.0f;
    defaultAtomMaterial.emission[1] = 0.0f;
    defaultAtomMaterial.emission[2] = 0.0f;
    defaultAtomMaterial.emission[3] = 1.0f;
    
    defaultBondMaterial.face = GL_FRONT;
    defaultBondMaterial.ambient[0] = 1.0f;
    defaultBondMaterial.ambient[1] = 1.0f;
    defaultBondMaterial.ambient[2] = 1.0f;
    defaultBondMaterial.ambient[3] = 1.0f;
    
    defaultBondMaterial.diffuse[0] = 1.0f;
    defaultBondMaterial.diffuse[1] = 1.0f;
    defaultBondMaterial.diffuse[2] = 1.0f;
    defaultBondMaterial.diffuse[3] = 1.0f;
    
    defaultBondMaterial.specular[0] = 0.5f;
    defaultBondMaterial.specular[1] = 0.5f;
    defaultBondMaterial.specular[2] = 0.5f;
    defaultBondMaterial.specular[3] = 1.0f;
    
    defaultBondMaterial.shininess = 35.0;
    
    defaultBondMaterial.emission[0] = 0.0f;
    defaultBondMaterial.emission[1] = 0.0f;
    defaultBondMaterial.emission[2] = 0.0f;
    defaultBondMaterial.emission[3] = 1.0f;
}


void NXOpenGLRenderingEngine::initializeGL(void)
{
    /// @todo change background to sky-blue gradient
    glClearColor(1.0, 1.0, 1.0, 1.0);
    glClearDepth(1.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    
    glEnable(GL_LIGHTING);
    glEnable(GL_DEPTH_TEST);
    
    /// @todo initialize light model
    setupDefaultLights();

    /// @todo anything else?
    // Initialize the modelview matrix
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    gluLookAt(0.0, 0.0, 1.0,
              0.0, 0.0, 0.0,
              0.0, 1.0, 0.0);
    
    glViewport(0, 0, width(), height());
    
    // Initialize the projection matrix
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluPerspective(55, (GLdouble)width()/(GLdouble)height(), 0.1, 50);
    
    // Initialize camera from current OpenGL settings
    camera.glGet();
}


void NXOpenGLRenderingEngine::setupDefaultLights(void)
{
    // light model
    lightModel.setLocalViewer(1);
    lightModel.setTwoSide(0);
    lightModel.set();
    
    // initialize light data
    GLint numSupportedOpenGLLights = 0;
    glGetIntegerv(GL_MAX_LIGHTS, &numSupportedOpenGLLights);
    lights.clear();
    for(GLint iLight=GL_LIGHT0;
        iLight<GL_LIGHT0+numSupportedOpenGLLights;
        ++iLight)
    {
        lights.push_back(GltLight(iLight));
    }
    
    GltColor const WHITE(1.0,1.0,1.0,1.0);
    lights[0].isEnabled() = true;
    lights[0].ambient() = 0.1 * WHITE;
    lights[0].diffuse() = 0.5 * WHITE;
    lights[0].specular() = 0.5 * WHITE;
    lights[0].position() = Vector(-50.0, 70.0, 30.0);
    lights[0].isDirectional() = true;
    lights[0].inEyeSpace() = true;
    lights[0].set();
    
    lights[1].isEnabled() = true;
    lights[1].ambient() = 0.1 * WHITE;
    lights[1].diffuse() = 0.5 * WHITE;
    lights[1].specular() = 0.5 * WHITE;
    lights[1].position() = Vector(-20.0, 20.0, 20.0);
    lights[1].isDirectional() = true;
    lights[1].inEyeSpace() = true;
    lights[1].set();
    
    for(GLint iLight=GL_LIGHT0+2; iLight<GL_LIGHT0+numSupportedOpenGLLights; ++iLight) {
        lights[iLight].isEnabled() = false;
        lights[iLight].ambient() = 0.1 * WHITE;
        lights[iLight].diffuse() = 0.5 * WHITE;
        lights[iLight].specular() = 0.5 * WHITE;
        lights[iLight].position() = Vector(0.0, 0.0, 100.0);
        lights[iLight].set();
    }
    
}


void NXOpenGLRenderingEngine::resizeGL(int width, int height)
{
    camera.resizeViewport(width, height);
    camera.glSetViewport();
    /// @todo set projection mode by calling camera method
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    gluPerspective(55, (GLdouble)width/(GLdouble)height, 0.1, 50);
    camera.glGetProjection();
    camera.glGetViewport();
    
/*    if(isOrthographicProjection)
        orthographicProjection.set();
    else
        perspectiveProjection.set();
    
    viewport.set((GLint) width, (GLint) height);*/
}


void NXOpenGLRenderingEngine::paintGL(void)
{
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    camera.glSetPosition();
    // drawSkyBlueBackground();
    rootSceneGraphNode->applyRecursive();
    glFlush();
    swapBuffers();
}


void NXOpenGLRenderingEngine::drawSkyBlueBackground(void)
{
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    /// @todo create a square with appropriate vertex colors
    // look up
    // * GLPane.py::standard_repaint_self0()
    // * drawer.py::drawFullWindow()
    
}


NXSGNode*
    NXOpenGLRenderingEngine::createSceneGraph(NXMoleculeSet *const molSetPtr)
{
    // create a copy of the color map to pass to plugins
    
    NXSGNode *moleculeSetNode = new NXSGNode;
    OBMolIterator molIter;
    for(molIter = molSetPtr->moleculesBegin();
        molIter != molSetPtr->moleculesEnd();
        ++molIter)
    {
        NXSGNode* molNode = createSceneGraph(*molIter);
        if(molNode) moleculeSetNode->addChild(molNode);
    }
    
    NXMoleculeSetIterator childrenIter;
    for(childrenIter = molSetPtr->childrenBegin();
        childrenIter != molSetPtr->childrenEnd();
        ++childrenIter)
    {
        NXSGNode *childMoleculeSetNode = createSceneGraph(*childrenIter);
        moleculeSetNode->addChild(childMoleculeSetNode);
    }
    return moleculeSetNode;
}


NXSGNode* NXOpenGLRenderingEngine::createSceneGraph(OBMol *const molPtr)
{
    Vector const canonicalZAxis(0.0, 0.0, 1.0);
    set<OBAtom*> renderedAtoms; // tracks atoms already rendered
    OBAtomIterator atomIter;
    
    // first atom
    OBAtom *firstAtomPtr = molPtr->BeginAtom(atomIter);
    if(firstAtomPtr == (OBAtom*) NULL) return (NXSGNode*) NULL;
    
    Vector const firstAtomPosition(firstAtomPtr->GetX(),
                                   firstAtomPtr->GetY(),
                                   firstAtomPtr->GetZ());
    
    NXSGOpenGLTranslate *rootMoleculeNode =
        new NXSGOpenGLTranslate(firstAtomPosition.x(),
                                firstAtomPosition.y(),
                                firstAtomPosition.z());
    NXSGNode *firstAtomNode =
        createSceneGraph(molPtr,
                         firstAtomPtr,
                         renderedAtoms,
                         canonicalZAxis);
    rootMoleculeNode->addChild(firstAtomNode);
    
    // rest of the atoms
    OBAtom *atomPtr = molPtr->NextAtom(atomIter);
    while(atomPtr != (OBAtom*) NULL) {
        set<OBAtom*>::iterator memberIter = renderedAtoms.find(atomPtr);
        if(memberIter == renderedAtoms.end()) { // atom not already rendered
            Vector const atomPosition(atomPtr->GetX(),
                                      atomPtr->GetY(),
                                      atomPtr->GetZ());
            Vector const atomRelativePosition = 
                (atomPosition - firstAtomPosition);
            // move scenegraph "cursor" to this atom
            NXSGOpenGLTranslate *translateToAtomNode =
                new NXSGOpenGLTranslate(atomRelativePosition.x(),
                                        atomRelativePosition.y(),
                                        atomRelativePosition.z());
            rootMoleculeNode->addChild(translateToAtomNode);
            // render subscenegraph rooted at this atom
            NXSGNode *atomNode = createSceneGraph(molPtr,
                                                  atomPtr,
                                                  renderedAtoms,
                                                  canonicalZAxis);
            translateToAtomNode->addChild(atomNode);
        }
        atomPtr = molPtr->NextAtom(atomIter);
    }
    return rootMoleculeNode;
}


NXSGNode*
    NXOpenGLRenderingEngine::createSceneGraph(OBMol *const molPtr,
                                              OBAtom *const atomPtr,
                                              set<OBAtom*>& renderedAtoms,
                                              Vector const& zAxis)
{
    // Precondition: *atomPtr shouldn't have been rendered
    assert(renderedAtoms.find(atomPtr) == renderedAtoms.end());
    
    // Do nothing if no rendering plugins
    if(pluginList.empty()) return (NXSGNode*) NULL;
    
    // translate origin to atom center
    Vector atomPosition(atomPtr->GetX(), atomPtr->GetY(), atomPtr->GetZ());
    
    // default color
    NXRGBColor defaultElementColor(0.0, 0.0, 0.0);
    map<uint, NXRGBColor>::iterator defaultElementColorIter =
        elementColorMap.find(atomPtr->GetAtomicNum());
    if(defaultElementColorIter != elementColorMap.end())
        defaultElementColor = defaultElementColorIter->second;
        
    // set default material parameters
    defaultAtomMaterial.ambient[0] = defaultElementColor.r;
    defaultAtomMaterial.ambient[1] = defaultElementColor.g;
    defaultAtomMaterial.ambient[2] = defaultElementColor.b;
    defaultAtomMaterial.ambient[3] = 1.0;
    defaultAtomMaterial.diffuse[0] = defaultElementColor.r;
    defaultAtomMaterial.diffuse[1] = defaultElementColor.g;
    defaultAtomMaterial.diffuse[2] = defaultElementColor.b;
    defaultAtomMaterial.diffuse[3] = 1.0;
    defaultAtomMaterial.specular[0] = defaultElementColor.r;
    defaultAtomMaterial.specular[1] = defaultElementColor.g;
    defaultAtomMaterial.specular[2] = defaultElementColor.b;
    defaultAtomMaterial.specular[3] = 1.0;
    
    // create scenegraph node and mark atom as rendered
    NXAtomRenderData atomRenderData(atomPtr->GetAtomicNum());
    atomRenderData.addData(static_cast<void const *>(&defaultAtomMaterial));
    NXSGNode *const atomNode =
        (*currentPluginIter)->renderAtom(atomRenderData);
    renderedAtoms.insert(atomPtr); // mark as rendered
    
    // render outgoing bonds and neighbouring atoms (if applicable) as children
    OBBondIterator bondIter;
    OBBond *bondPtr(NULL);
    for(bondPtr = atomPtr->BeginBond(bondIter);
        bondPtr != NULL;
        bondPtr = atomPtr->NextBond(bondIter))
    {
        // compute bond orientation
        OBAtom *const nbrAtomPtr = bondPtr->GetNbrAtom(atomPtr);
        Vector const nbrAtomPosition(nbrAtomPtr->GetX(),
                                     nbrAtomPtr->GetY(),
                                     nbrAtomPtr->GetZ());
        Vector newZAxis = (nbrAtomPosition - atomPosition);
        newZAxis.normalize();
        Vector const rotationAxis = xProduct(zAxis, newZAxis);
        real const rotationAngle = newZAxis * zAxis;
        
        // align z-axis with bond
        NXSGOpenGLRotate *const rotateZAxisNode =
            new NXSGOpenGLRotate(rotationAngle,
                                 rotationAxis.x(),
                                 rotationAxis.y(),
                                 rotationAxis.z());
        atomNode->addChild(rotateZAxisNode);
        void const *const defBondMatPtr = 
            static_cast<void const*>(&defaultBondMaterial);
        NXBondRenderData bondRenderData(bondPtr->GetBondOrder(),
                                        bondPtr->GetLength());
        bondRenderData.addData(defBondMatPtr);
        NXSGNode *const bondNode = 
            (*currentPluginIter)->renderBond(bondRenderData);
        rotateZAxisNode->addChild(bondNode);
        
        
        double const bondLength = bondPtr->GetLength();
        NXSGOpenGLTranslate *const translateToNbrAtomNode =
            new NXSGOpenGLTranslate(0.0, 0.0, bondLength);
        bondNode->addChild(translateToNbrAtomNode);
        
        set<OBAtom*>::iterator memberIter = renderedAtoms.find(nbrAtomPtr);
        // render neighbouring atom not already done
        if(memberIter == renderedAtoms.end()) { 
            NXSGNode *nbrAtomNode = createSceneGraph(molPtr,
                                                     nbrAtomPtr,
                                                     renderedAtoms,
                                                     atomPosition);
            translateToNbrAtomNode->addChild(nbrAtomNode);
        }
    }
    
    renderedAtoms.insert(atomPtr);
    return atomNode;
}


void NXOpenGLRenderingEngine::resetView(void)
{
    if(rootMoleculeSet == NULL) return;
    
    // create axis-aligned bounding box
    /// @todo
    BoundingBox bbox = GetMoleculeSetBoundingBox(rootMoleculeSet);
    Vector bboxMin = 1.5 * bbox.min();
    Vector bboxMax = 1.5 * bbox.max();
    
    camera.glFrustum(bboxMin.x(), bboxMax.x(),
                     bboxMin.y(), bboxMax.y(),
                     bboxMin.z(), bboxMax.z());
    updateGL();
}


BoundingBox
    NXOpenGLRenderingEngine::
    GetMoleculeSetBoundingBox(NXMoleculeSet *const molSetPtr)
{
    
    BoundingBox bbox;
    
    // include all atoms
    OBMolIterator molIter;
    for(molIter = molSetPtr->moleculesBegin();
        molIter != molSetPtr->moleculesEnd();
        ++molIter)
    {
        OBMol *const molPtr = *molIter;
        bbox += GetMoleculeBoundingBox(molPtr);
    }
    
    // include children molecule-sets
    NXMoleculeSetIterator molSetIter;
    for(molSetIter = molSetPtr->childrenBegin();
        molSetIter != molSetPtr->childrenEnd();
        ++molSetIter)
    {
        NXMoleculeSet *const molSetPtr = *molSetIter;
        bbox += GetMoleculeSetBoundingBox(molSetPtr);
    }
    return bbox;
}


BoundingBox
    NXOpenGLRenderingEngine::GetMoleculeBoundingBox(OBMol *const molPtr)
{
    BoundingBox bbox;
    OBAtomIterator atomIter;
    OBAtom *atomPtr = NULL;
    
    for(atomPtr = molPtr->BeginAtom(atomIter);
        atomPtr != NULL;
        atomPtr = molPtr->NextAtom(atomIter))
    {
        Vector atomPos(real(atomPtr->GetX()),
                       real(atomPtr->GetY()),
                       real(atomPtr->GetZ()));
        bbox += atomPos;
    }
    
    return bbox;
}


void NXOpenGLRenderingEngine::mousePressEvent(QMouseEvent *mouseEvent)
{
    if(mouseEvent->button() == Qt::MidButton &&
       mouseEvent->modifiers() == Qt::NoModifier)
    {
        camera.rotateStartEvent(mouseEvent->x(), mouseEvent->y());
        mouseEvent->accept();
    }
    else
        mouseEvent->ignore();
    
    updateGL();
}


void NXOpenGLRenderingEngine::mouseMoveEvent(QMouseEvent *mouseEvent)
{
    assert(mouseEvent->button() == Qt::NoButton);
    
    if(mouseEvent->modifiers() == Qt::NoModifier)
    {
        camera.rotatingEvent(mouseEvent->x(), mouseEvent->y());
        mouseEvent->accept();
    }
    else
        mouseEvent->ignore();
    
    updateGL();
}


void NXOpenGLRenderingEngine::mouseReleaseEvent(QMouseEvent *mouseEvent)
{
    if(mouseEvent->button() == Qt::MidButton)
    {
        camera.rotateStopEvent(mouseEvent->x(), mouseEvent->y());
        mouseEvent->accept();
    }
    else
        mouseEvent->ignore();
    
    updateGL();
}

} // Nanorex
